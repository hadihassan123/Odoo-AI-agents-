odoo.define('ai_studio.chat_widget', function (require) {
    "use strict";

    const rpc = require('web.rpc');

    const ChatWidget = {
        start: function () {

            const box = document.createElement('div');
            box.innerHTML = `
                <div id="ai-chat-box" style="
                    position: fixed;
                    bottom: 80px;
                    right: 20px;
                    width: 300px;
                    height: 400px;
                    background: white;
                    border: 1px solid #ccc;
                    z-index: 999999;
                ">
                    <div id="messages" style="height: 350px; overflow:auto;"></div>
                    <input id="input" style="width: 100%;" placeholder="Ask AI..." />
                </div>
            `;

            document.body.appendChild(box);

            document.getElementById("input").addEventListener("keydown", function(e){
                if (e.key === "Enter") {

                    const msg = this.value;

                    rpc.query({
                        route: '/ai/chat',
                        params: { message: msg }
                    }).then(function (result) {

                        const messages = document.getElementById("messages");

                        messages.innerHTML += `<div><b>You:</b> ${msg}</div>`;
                        messages.innerHTML += `<div><b>AI:</b> ${result.reply}</div>`;
                    });

                    this.value = "";
                }
            });
        }
    };

    return ChatWidget;
});


// ✅ STEP 4 — ADD THIS PART AT THE BOTTOM (same file)

odoo.define('ai_studio.chat_init', function (require) {
    "use strict";

    const ChatWidget = require('ai_studio.chat_widget');

    document.addEventListener("DOMContentLoaded", function () {
        ChatWidget.start();
    });
});
// odoo.define('ai_studio.chat_widget', function (require) {
//     "use strict";
//
//     const rpc = require('web.rpc');
//
//     const ChatWidget = {
//         start: function () {
//
//             const box = document.createElement('div');
//             box.innerHTML = `
//                 <div id="ai-chat-box" style="
//                     position: fixed;
//                     bottom: 20px;
//                     right: 20px;
//                     width: 300px;
//                     height: 400px;
//                     background: white;
//                     border: 1px solid #ccc;
//                     z-index: 9999;
//                 ">
//                     <div id="messages" style="height: 350px; overflow:auto;"></div>
//                     <input id="input" style="width: 100%;" placeholder="Ask AI..." />
//                 </div>
//             `;
//
//             document.body.appendChild(box);
//
//             document.getElementById("input").addEventListener("keydown", function(e){
//                 if (e.key === "Enter") {
//
//                     const msg = this.value;
//
//                     rpc.query({
//                         route: '/ai/chat',
//                         params: { message: msg }
//                     }).then(function (result) {
//
//                         const messages = document.getElementById("messages");
//
//                         messages.innerHTML += `<div><b>You:</b> ${msg}</div>`;
//                         messages.innerHTML += `<div><b>AI:</b> ${result.reply}</div>`;
//                     });
//
//                     this.value = "";
//                 }
//             });
//         }
//     };
//
//     return ChatWidget;
// });