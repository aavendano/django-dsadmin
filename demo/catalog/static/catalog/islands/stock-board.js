/**
 * Stock board island — a standalone ES module, no build step.
 * Contract: export mount(element, props, context) and optionally return an
 * unmount function. `context.csrfToken` is available for POSTs to Django.
 * Only design-system classes (d-*) are used, so it follows the active theme.
 */
export function mount(root, props, context) {
  const state = { filter: "all", query: "" };
  const products = props.products || [];
  const threshold = props.threshold ?? 10;

  root.innerHTML = `
    <div class="flex flex-col gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <label class="d-input d-input-sm w-full max-w-xs">
          <span class="sr-only">Filter products</span>
          <input type="search" placeholder="Filter by name or SKU" data-q class="grow">
        </label>
        <div class="d-join" role="group" aria-label="Stock level">
          <button type="button" class="d-btn d-btn-sm d-join-item d-btn-active" data-f="all" aria-pressed="true">All</button>
          <button type="button" class="d-btn d-btn-sm d-join-item" data-f="low" aria-pressed="false">Low</button>
          <button type="button" class="d-btn d-btn-sm d-join-item" data-f="ok" aria-pressed="false">OK</button>
        </div>
        <span class="text-sm opacity-70" data-count aria-live="polite"></span>
      </div>
      <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3" data-list></ul>
    </div>`;

  const list = root.querySelector("[data-list]");
  const count = root.querySelector("[data-count]");

  function render() {
    const q = state.query.toLowerCase();
    const items = products.filter((p) => {
      const low = p.stock < threshold;
      if (state.filter === "low" && !low) return false;
      if (state.filter === "ok" && low) return false;
      return !q || p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q);
    });
    count.textContent = `${items.length} of ${products.length}`;
    list.replaceChildren(
      ...items.map((p) => {
        const li = document.createElement("li");
        const low = p.stock < threshold;
        li.className = "d-card theme-bordered bg-base-100";
        li.innerHTML = `
          <div class="d-card-body gap-1 p-3">
            <div class="flex items-start justify-between gap-2">
              <a class="d-link d-link-hover font-semibold" href="${props.changeUrl}${p.id}/change/"></a>
              <span class="d-badge d-badge-sm ${low ? "d-badge-error" : "d-badge-success"}"></span>
            </div>
            <span class="text-xs opacity-70 font-mono"></span>
            <progress class="d-progress ${low ? "d-progress-error" : "d-progress-success"} h-2 w-full" max="200"></progress>
          </div>`;
        li.querySelector("a").textContent = p.name;
        li.querySelector(".d-badge").textContent = `${p.stock} units`;
        li.querySelector(".font-mono").textContent = p.sku;
        const bar = li.querySelector("progress");
        bar.value = Math.min(p.stock, 200);
        bar.setAttribute("aria-label", `${p.name}: ${p.stock} units`);
        return li;
      }),
    );
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "col-span-full py-6 text-center text-sm opacity-70";
      li.textContent = "No products match.";
      list.append(li);
    }
  }

  const onInput = (e) => { state.query = e.target.value; render(); };
  const onClick = (e) => {
    const btn = e.target.closest("[data-f]");
    if (!btn) return;
    state.filter = btn.dataset.f;
    root.querySelectorAll("[data-f]").forEach((b) => {
      const on = b === btn;
      b.classList.toggle("d-btn-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    render();
  };
  root.querySelector("[data-q]").addEventListener("input", onInput);
  root.addEventListener("click", onClick);
  render();

  return () => {
    root.removeEventListener("click", onClick);
    root.innerHTML = "";
  };
}
