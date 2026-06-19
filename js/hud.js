// The 2D overlay: the gem counter, the status pill ("Solved!" / "Keep trying"),
// and the in-scene Run button.

export class Hud {
  constructor(el, onRun) {
    this.el = el;
    this._buildCounter();
    this._buildButton(onRun);
  }

  _buildCounter() {
    const hud = document.createElement("div");
    hud.className = "wanderland-hud";
    this.gemsEl = document.createElement("div");
    this.gemsEl.className = "wanderland-hud-gems";
    this.statusEl = document.createElement("div");
    this.statusEl.className = "wanderland-hud-status";
    hud.appendChild(this.gemsEl);
    hud.appendChild(this.statusEl);
    this.el.appendChild(hud);
    this._hud = hud;
    this.setScore(0, 0);
  }

  _buildButton(onRun) {
    const bar = document.createElement("div");
    bar.className = "wanderland-controls";
    const btn = document.createElement("button");
    btn.className = "wanderland-run-btn";
    btn.type = "button";
    btn.addEventListener("click", () => onRun && onRun());
    bar.appendChild(btn);
    this.el.appendChild(bar);
    this._bar = bar;
    this.runBtn = btn;
    this.setButton("empty");
  }

  setScore(score, total) {
    this.gemsEl.innerHTML = `<span class="wanderland-gem-icon">◆</span> ${score} / ${total}`;
  }

  setStatus(text, kind) {
    this.statusEl.textContent = text;
    this.statusEl.dataset.kind = kind || "";
    this.statusEl.style.opacity = "1";
  }

  hideStatus() {
    this.statusEl.style.opacity = "0";
  }

  setButton(state) {
    const btn = this.runBtn;
    btn.dataset.state = state;
    if (state === "running") {
      btn.disabled = true;
      btn.innerHTML = '<span class="wanderland-run-spin"></span> Running…';
    } else if (state === "empty") {
      btn.disabled = true;
      btn.innerHTML = '<span class="wanderland-run-icon">▶</span> Run My Code';
    } else {
      btn.disabled = false;
      const label = state === "done" ? "Run Again" : "Run My Code";
      btn.innerHTML = `<span class="wanderland-run-icon">▶</span> ${label}`;
    }
  }

  dispose() {
    if (this._hud && this._hud.parentNode) this._hud.remove();
    if (this._bar && this._bar.parentNode) this._bar.remove();
  }
}
