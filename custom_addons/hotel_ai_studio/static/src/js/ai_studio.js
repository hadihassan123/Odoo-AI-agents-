/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

const STORAGE_KEY = "hotel_ai_studio.chat_state";
const MODES = [
    { value: "groq", label: "Groq", empty: "Ask Groq anything about your Odoo work." },
    { value: "hotel_data", label: "Hotel Data", empty: "Ask about hotel records and operations." },
    { value: "pipeline", label: "Pipeline", empty: "Use the development pipeline for code generation and review." },
    { value: "slave", label: "Slave", empty: "Type start to begin creating a module." },
];
const DEFAULT_MODE = "groq";

function createSession() {
    return {
        history: [],
        slave_step: 0,
        slave_data: "{}",
        isWaiting: false,
        status: "",
    };
}

function createSessions() {
    return Object.fromEntries(MODES.map((mode) => [mode.value, createSession()]));
}

function defaultState() {
    return {
        isOpen: false,
        activeMode: DEFAULT_MODE,
        sessions: createSessions(),
    };
}

function normalizeSessions(rawSessions) {
    const sessions = createSessions();
    for (const mode of MODES) {
        const raw = rawSessions?.[mode.value] || {};
        sessions[mode.value] = {
            ...createSession(),
            ...raw,
            history: Array.isArray(raw.history) ? raw.history.slice(-40) : [],
            isWaiting: false,
            status: raw.status || "",
        };
    }
    return sessions;
}

function migrateLegacyState(parsed) {
    const state = defaultState();
    const legacyMode = MODES.some((mode) => mode.value === parsed?.mode) ? parsed.mode : DEFAULT_MODE;
    const legacySession = {
        ...createSession(),
        history: Array.isArray(parsed?.history) ? parsed.history.slice(-40) : [],
        slave_step: Number.isInteger(parsed?.slave_step) ? parsed.slave_step : 0,
        slave_data: typeof parsed?.slave_data === "string" ? parsed.slave_data : "{}",
    };
    state.isOpen = Boolean(parsed?.isOpen);
    state.activeMode = legacyMode;
    state.sessions[legacyMode] = legacySession;
    return state;
}

function loadState() {
    try {
        const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
        if (parsed?.sessions) {
            return {
                isOpen: Boolean(parsed.isOpen),
                activeMode: MODES.some((mode) => mode.value === parsed.activeMode)
                    ? parsed.activeMode
                    : DEFAULT_MODE,
                sessions: normalizeSessions(parsed.sessions),
            };
        }
        return migrateLegacyState(parsed);
    } catch {
        return defaultState();
    }
}

function saveState(state) {
    const snapshot = {
        isOpen: state.isOpen,
        activeMode: state.activeMode,
        sessions: {},
    };
    for (const mode of MODES) {
        const session = state.sessions[mode.value] || createSession();
        snapshot.sessions[mode.value] = {
            history: session.history.slice(-40),
            slave_step: session.slave_step,
            slave_data: session.slave_data,
            status: session.status || "",
        };
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

function escapeHtml(text) {
    return String(text || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function normalizeResponse(result) {
    if (result && typeof result === "object" && "response" in result) {
        return {
            response: result.response || "",
            slave_step: result.slave_step || 0,
            slave_data: result.slave_data || "{}",
            error: Boolean(result.error),
        };
    }
    return {
        response: "",
        slave_step: 0,
        slave_data: "{}",
        error: true,
    };
}

function isAiStudioScreen() {
    const hash = window.location.hash || "";
    const path = window.location.pathname || "";
    if (path === "/ai_studio") {
        return true;
    }
    if (hash.includes("model=ai.studio.chat") || hash.includes("action=ai_studio_action")) {
        return true;
    }
    return Boolean(
        document.querySelector('.o_form_view[data-model="ai.studio.chat"]') ||
        document.querySelector(".ai_studio_screen_root")
    );
}

class AiStudioChat {
    constructor() {
        this.state = loadState();
        this.floatingRoot = null;
        this.embeddedRoot = null;
        this.hashListener = () => this.render();
        this.domObserver = null;
        this.pendingDomRefresh = false;
        this.lastHash = window.location.hash || "";
        this.lastPath = window.location.pathname || "";
        this.lastAiScreenState = false;
        this.currentMode = this.state.activeMode;
    }

    scheduleDomRefresh() {
        if (this.pendingDomRefresh) {
            return;
        }
        this.pendingDomRefresh = true;
        window.requestAnimationFrame(() => {
            this.pendingDomRefresh = false;
            const currentHost = document.querySelector(".ai_studio_screen_root");
            const nextHash = window.location.hash || "";
            const nextPath = window.location.pathname || "";
            const nextAiScreenState = isAiStudioScreen();
            const hostChanged = currentHost !== this.embeddedRoot;
            const routeChanged = nextHash !== this.lastHash || nextPath !== this.lastPath;
            const screenChanged = nextAiScreenState !== this.lastAiScreenState;
            if (hostChanged || routeChanged || screenChanged) {
                this.render();
            }
        });
    }

    getSession(mode = this.currentMode) {
        if (!this.state.sessions[mode]) {
            this.state.sessions[mode] = createSession();
        }
        return this.state.sessions[mode];
    }

    setMode(mode) {
        if (!MODES.some((entry) => entry.value === mode)) {
            return;
        }
        this.currentMode = mode;
        this.state.activeMode = mode;
        this.render();
    }

    resetConversation(mode = this.currentMode) {
        this.state.sessions[mode] = createSession();
        this.render();
    }

    async sendMessage(source) {
        const input = source.querySelector(".hai-input");
        const text = input.value.trim();
        const session = this.getSession();
        if (!text || session.isWaiting) {
            return;
        }

        session.history.push({ role: "user", content: text });
        session.isWaiting = true;
        session.status = "";
        input.value = "";
        this.render();

        try {
            const result = await rpc("/ai_studio/send", {
                message: text,
                mode: this.currentMode,
                history: JSON.stringify(session.history.slice(-20)),
                slave_step: session.slave_step,
                slave_data: session.slave_data,
            });
            const payload = normalizeResponse(result);
            session.history.push({ role: "assistant", content: payload.response });
            session.slave_step = payload.slave_step;
            session.slave_data = payload.slave_data;
            session.status = payload.error ? "Request failed." : "";
        } catch (error) {
            session.history.push({
                role: "assistant",
                content: `Request failed: ${error.message || error}`,
            });
            session.status = "Request failed.";
        }

        session.isWaiting = false;
        this.render();
    }

    bindRoot(root) {
        root.addEventListener("click", (event) => {
            const tab = event.target.closest("[data-ai-mode]");
            if (tab) {
                this.setMode(tab.dataset.aiMode);
                return;
            }

            if (event.target.closest(".hai-clear")) {
                this.resetConversation();
                return;
            }

            if (event.target.closest(".hai-send")) {
                this.sendMessage(root);
                return;
            }

            if (event.target.closest(".hai-toggle")) {
                this.state.isOpen = !this.state.isOpen;
                this.render();
                return;
            }

            if (event.target.closest(".hai-close")) {
                this.state.isOpen = false;
                this.render();
            }
        });

        root.addEventListener("keydown", (event) => {
            const input = event.target.closest(".hai-input");
            if (!input) {
                return;
            }
            event.stopPropagation();
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage(root);
            }
        });

        root.addEventListener("keyup", (event) => {
            if (event.target.closest(".hai-input")) {
                event.stopPropagation();
            }
        });

        root.addEventListener("keypress", (event) => {
            if (event.target.closest(".hai-input")) {
                event.stopPropagation();
            }
        });
    }

    buildTabs() {
        return MODES.map((mode) => `
            <button
                type="button"
                class="hai-tab ${mode.value === this.currentMode ? "is-active" : ""}"
                data-ai-mode="${mode.value}"
            >
                ${mode.label}
            </button>
        `).join("");
    }

    buildMessages(session) {
        if (!session.history.length) {
            const mode = MODES.find((entry) => entry.value === this.currentMode);
            return `<div class="hai-empty">${escapeHtml(mode?.empty || "Ask a question to start.")}</div>`;
        }

        return session.history.slice(-40).map((message) => {
            const roleClass = message.role === "user" ? "is-user" : "is-assistant";
            const label = message.role === "user" ? "You" : "AI";
            return `
                <article class="hai-message ${roleClass}">
                    <div class="hai-badge">${label}</div>
                    <div class="hai-bubble">${escapeHtml(message.content).replace(/\n/g, "<br/>")}</div>
                </article>
            `;
        }).join("");
    }

    buildComposer(compact = false) {
        const session = this.getSession();
        return `
            <div class="hai-shell ${compact ? "is-compact" : "is-embedded"}">
                <div class="hai-toolbar">
                    <div class="hai-tabs" role="tablist" aria-label="AI Studio modes">
                        ${this.buildTabs()}
                    </div>
                    <button type="button" class="hai-clear">New Chat</button>
                </div>
                <div class="hai-slave-tip" ${this.currentMode === "slave" ? "" : 'hidden="hidden"'}>
                    In Slave mode, type <code>start</code> to begin module creation.
                </div>
                <div class="hai-messages">${this.buildMessages(session)}</div>
                <div class="hai-status" aria-live="polite">
                    ${session.isWaiting ? "Waiting for AI..." : escapeHtml(session.status)}
                </div>
                <div class="hai-composer">
                    <textarea
                        class="hai-input"
                        rows="${compact ? "3" : "4"}"
                        placeholder="Type a message..."
                        ${session.isWaiting ? 'disabled="disabled"' : ""}
                    ></textarea>
                    <button type="button" class="hai-send" ${session.isWaiting ? 'disabled="disabled"' : ""}>
                        Send
                    </button>
                </div>
            </div>
        `;
    }

    mountFloating() {
        if (document.getElementById("hotel-ai-studio-chat-root")) {
            return true;
        }
        const anchor = document.querySelector(".o_web_client");
        if (!anchor) {
            return false;
        }

        this.floatingRoot = document.createElement("div");
        this.floatingRoot.id = "hotel-ai-studio-chat-root";
        this.floatingRoot.setAttribute("contenteditable", "false");
        this.bindRoot(this.floatingRoot);
        anchor.appendChild(this.floatingRoot);
        return true;
    }

    mountEmbedded() {
        const host = document.querySelector(".ai_studio_screen_root");
        if (!host) {
            this.embeddedRoot = null;
            return;
        }
        this.embeddedRoot = host;
        if (!host.dataset.aiStudioBound) {
            this.bindRoot(host);
            host.dataset.aiStudioBound = "1";
        }
    }

    renderFloating() {
        if (!this.floatingRoot) {
            return;
        }

        const hiddenOnThisScreen = isAiStudioScreen();
        this.floatingRoot.style.display = hiddenOnThisScreen ? "none" : "";
        this.floatingRoot.className = this.state.isOpen ? "is-open" : "";
        this.floatingRoot.innerHTML = `
            <button type="button" class="hai-toggle">${this.state.isOpen ? "Close AI" : "AI Studio"}</button>
            <section class="hai-panel">
                <header class="hai-header">
                    <div>
                        <h3>Hotel AI Studio</h3>
                        <p>Each tab keeps its own chat history.</p>
                    </div>
                    <button type="button" class="hai-close" aria-label="Close">×</button>
                </header>
                ${this.buildComposer(true)}
            </section>
        `;

        const messages = this.floatingRoot.querySelector(".hai-messages");
        if (messages) {
            messages.scrollTop = messages.scrollHeight;
        }
    }

    renderEmbedded() {
        if (!this.embeddedRoot) {
            return;
        }

        this.embeddedRoot.classList.add("is-mounted");
        this.embeddedRoot.innerHTML = `
            <section class="ai_studio_screen">
                <header class="ai_studio_screen_header">
                    <div>
                        <h2>Hotel AI Studio</h2>
                        <p>Switch tabs to keep separate conversations for each assistant mode.</p>
                    </div>
                </header>
                ${this.buildComposer()}
            </section>
        `;

        const messages = this.embeddedRoot.querySelector(".hai-messages");
        if (messages) {
            messages.scrollTop = messages.scrollHeight;
        }
    }

    render() {
        this.mountEmbedded();
        this.renderFloating();
        this.renderEmbedded();
        this.lastHash = window.location.hash || "";
        this.lastPath = window.location.pathname || "";
        this.lastAiScreenState = isAiStudioScreen();
        saveState(this.state);
    }

    start() {
        if (!this.mountFloating()) {
            return false;
        }
        this.mountEmbedded();
        window.addEventListener("hashchange", this.hashListener);
        this.domObserver = new MutationObserver(() => this.scheduleDomRefresh());
        this.domObserver.observe(document.body, { childList: true, subtree: true });
        this.render();
        return true;
    }
}

function mountWhenReady() {
    if (!document.body || !document.querySelector(".o_web_client")) {
        window.setTimeout(mountWhenReady, 50);
        return;
    }
    const chat = new AiStudioChat();
    if (!chat.start()) {
        window.setTimeout(mountWhenReady, 50);
    }
}

mountWhenReady();
