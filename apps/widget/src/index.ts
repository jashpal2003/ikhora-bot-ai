/**
 * Relay Customer Web Widget
 * Embedded in customer sites. Uses Shadow DOM to isolate styles and prevent CSS collisions.
 */

class RelayWidgetElement extends HTMLElement {
  connectedCallback() {
    const shadow = this.attachShadow({ mode: "open" });
    const container = document.createElement("div");
    container.innerHTML = `
      <style>
        .relay-launcher {
          position: fixed;
          bottom: 20px;
          right: 20px;
          background: #4f46e5;
          color: white;
          width: 56px;
          height: 56px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          font-family: system-ui, sans-serif;
          z-index: 999999;
        }
      </style>
      <div class="relay-launcher" id="launcher">💬</div>
    `;
    shadow.appendChild(container);
  }
}

customElements.define("relay-chat-widget", RelayWidgetElement);
