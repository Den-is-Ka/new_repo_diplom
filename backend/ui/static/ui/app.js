// --- Tiny JWT client for Diplom UI ---
(() => {
  const API_BASE = () =>
    (window.DIPLOM && window.DIPLOM.API_BASE) ? window.DIPLOM.API_BASE : "";

  const LS = {
    access: "diplom.jwt.access",
    refresh: "diplom.jwt.refresh",
  };

  function getAccess() { return localStorage.getItem(LS.access); }
  function getRefresh() { return localStorage.getItem(LS.refresh); }

  function setTokens(access, refresh) {
    if (access) localStorage.setItem(LS.access, access);
    if (refresh) localStorage.setItem(LS.refresh, refresh);
  }

  function clearTokens() {
    localStorage.removeItem(LS.access);
    localStorage.removeItem(LS.refresh);
  }

  async function rawFetch(url, opts = {}) {
    return fetch(API_BASE() + url, opts);
  }

  async function refreshToken() {
    const refresh = getRefresh();
    if (!refresh) return false;

    const res = await rawFetch("/api/token/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ refresh }),
    });

    if (!res.ok) {
      clearTokens();
      return false;
    }
    const data = await res.json();
    setTokens(data.access, null);
    return true;
  }

  async function apiFetch(url, opts = {}) {
    const headers = new Headers(opts.headers || {});
    headers.set("Accept", "application/json");
    if (!headers.has("Content-Type") && opts.body) headers.set("Content-Type", "application/json");

    const access = getAccess();
    if (access) headers.set("Authorization", "Bearer " + access);

    const res = await rawFetch(url, { ...opts, headers });

    // если не 401 — просто возвращаем
    if (res.status !== 401) return res;

    // Try refresh and retry once
    const refreshed = await refreshToken();
    if (!refreshed) return res;

    const headers2 = new Headers(opts.headers || {});
    headers2.set("Accept", "application/json");
    if (!headers2.has("Content-Type") && opts.body) headers2.set("Content-Type", "application/json");
    const access2 = getAccess();
    if (access2) headers2.set("Authorization", "Bearer " + access2);

    return rawFetch(url, { ...opts, headers: headers2 });
  }

  async function jsonOrText(res) {
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) return res.json();
    return res.text();
  }

  async function ensureOk(res) {
    if (res.ok) return res;
    const body = await jsonOrText(res);
    const msg = (typeof body === "string") ? body : JSON.stringify(body);
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }

  async function login(username, password) {
    const res = await rawFetch("/api/token/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    await ensureOk(res);
    const data = await res.json();
    setTokens(data.access, data.refresh);
    return data;
  }

  // Registration endpoint
  // POST /api/users/register/  body: { username, password, email?, company_name? }
  async function register(username, password, email = "", company_name = "") {
    const res = await rawFetch("/api/users/register/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ username, password, email, company_name }),
    });
    await ensureOk(res);
    return res.json();
  }

  async function ensureAccessToken() {
    const a = getAccess();
    if (a) return true;
    return refreshToken();
  }

  function logout() { clearTokens(); }

  // --- helpers for module patching ---
  function normalizeModuleIds(items) {
    // items can be:
    // - [23, 24]
    // - [{id:23}, {id:24}]
    // - [{module:23, quantity:1}]
    if (!Array.isArray(items)) return [];
    const out = [];
    for (const it of items) {
      if (it == null) continue;
      if (typeof it === "number") out.push(it);
      else if (typeof it === "string" && it.trim() && !Number.isNaN(Number(it))) out.push(Number(it));
      else if (typeof it === "object") {
        const v = (it.module != null) ? it.module : it.id;
        if (typeof v === "number") out.push(v);
        else if (typeof v === "string" && v.trim() && !Number.isNaN(Number(v))) out.push(Number(v));
      }
    }
    // uniq
    return Array.from(new Set(out)).filter((x) => Number.isFinite(x) && x > 0);
  }

  // --- small helper for GET JSON list/paginated ---
  async function tryGetList(url) {
    try {
      const res = await apiFetch(url, { method: "GET" });
      if (!res.ok) return null;
      const data = await res.json();
      const list = data?.results ?? data;
      return Array.isArray(list) ? list : null;
    } catch {
      return null;
    }
  }

  // --- Catalog categories cache (IMPORTANT FIX for DGU missing) ---
  let _categoriesCache = null;
  async function getAllCategories() {
    if (_categoriesCache) return _categoriesCache;

    const res = await apiFetch("/api/catalog/equipment-categories/", { method: "GET" });
    await ensureOk(res);
    const data = await res.json();
    const list = data?.results ?? data;
    _categoriesCache = Array.isArray(list) ? list : [];
    return _categoriesCache;
  }

  function norm(s) {
    return String(s ?? "").trim().toLowerCase();
  }

  function getRootCategory(categories) {
    // Prefer equipment_type === "root"
    let root = categories.find(c => norm(c?.equipment_type) === "root");
    if (root) return root;

    // Fallback by name
    root = categories.find(c => norm(c?.name) === "оборудование");
    return root || null;
  }

  function idEq(a, b) {
    return String(a ?? "") === String(b ?? "");
  }

  // --- Diplom API wrappers ---
  const DiplomAPI = {
    // Categories (FIXED: use catalog endpoint, not configurator main_categories)
    async getMainCategories() {
      const cats = await getAllCategories();

      const root = getRootCategory(cats);
      if (root && root.id != null) {
        // main = children of "Оборудование"
        const out = cats.filter(c =>
          c &&
          c.id != null &&
          !idEq(c.id, root.id) &&
          idEq(c.parent, root.id)
        );
        return out;
      }

      // fallback: top-level (no parent) and not root-like
      return cats.filter(c =>
        c && c.parent == null && norm(c.equipment_type) !== "root" && norm(c.name) !== "оборудование"
      );
    },

    async getSubCategories(mainId) {
      const cats = await getAllCategories();
      return cats.filter(c => c && idEq(c.parent, mainId));
    },

    // Configurations
    async listConfigurations() {
      const res = await apiFetch("/api/configurator/configurations/", { method: "GET" });
      await ensureOk(res);
      const data = await res.json();
      return data.results || data;
    },

    async getConfiguration(id) {
      const res = await apiFetch(`/api/configurator/configurations/${id}/`, { method: "GET" });
      await ensureOk(res);
      return res.json();
    },

    async createConfiguration(payload) {
      const res = await apiFetch("/api/configurator/configurations/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await ensureOk(res);
      return res.json();
    },

    async patchConfiguration(id, payload) {
      const res = await apiFetch(`/api/configurator/configurations/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      await ensureOk(res);
      return res.json();
    },

    // ✅ P0 FIX:
    // UI раньше шёл с module_items/modules/items. Это не сохранялось через through.
    // Теперь всегда шлём {module_ids:[...]}.
    // Дополнительно: после patch делаем validate и подмешиваем total_price,
    // потому что GET конфигурации у вас пока может показывать 0.00.
    async patchConfigurationModules(id, items) {
      const moduleIds = normalizeModuleIds(items);
      if (!moduleIds.length) {
        throw new Error("No modules selected (module_ids is empty).");
      }

      // 1) patch modules via module_ids
      const patched = await this.patchConfiguration(id, { module_ids: moduleIds });

      // 2) try validate to get correct total_price right away (non-fatal)
      try {
        const v = await this.validateConfiguration(id);
        if (v && typeof v.total_price !== "undefined") {
          patched.total_price = v.total_price;
        }
        if (typeof v?.is_valid !== "undefined") patched.is_valid = v.is_valid;
        if (typeof v?.errors !== "undefined") patched.validation_errors = v.errors;
      } catch (_) {}

      return patched;
    },

    async getAvailableModules(categoryId) {
      const tries = [
        `/api/configurator/configurations/available_modules/?category_id=${encodeURIComponent(categoryId)}`,
        `/api/configurator/configurations/available_modules/?sub_category_id=${encodeURIComponent(categoryId)}`,
        `/api/configurator/configurations/available_modules/?sub_category=${encodeURIComponent(categoryId)}`,
      ];

      for (const url of tries) {
        const res = await apiFetch(url, { method: "GET" });
        if (res.ok) return res.json();
      }

      const res = await apiFetch("/api/configurator/configurations/available_modules/", { method: "GET" });
      await ensureOk(res);
      return res.json();
    },

    // ✅ FIX: payload под backend serializer (engineering_option_ids)
    async setEngineering(cfgId, engineeringIds) {
      const res = await apiFetch(`/api/configurator/configurations/${cfgId}/set_engineering/`, {
        method: "POST",
        body: JSON.stringify({
          engineering_option_ids: engineeringIds,
          engineering_systems: engineeringIds,
          engineering: engineeringIds,
          ids: engineeringIds,
        }),
      });
      await ensureOk(res);
      return res.json();
    },

    async validateConfiguration(cfgId) {
      const res = await apiFetch(`/api/configurator/configurations/${cfgId}/validate/`, { method: "GET" });
      await ensureOk(res);
      return res.json();
    },

    async submitConfiguration(cfgId) {
      const res = await apiFetch(`/api/configurator/configurations/${cfgId}/submit/`, { method: "POST" });
      await ensureOk(res);
      return res.json();
    },

    // Engineering list (robust)
    async getEngineeringList() {
      const options = await tryGetList("/api/catalog/engineering-system-options/");
      if (options && options.length) {
        const groups = await tryGetList("/api/catalog/engineering-system-groups/");
        const groupTitleById = {};
        if (groups && groups.length) {
          for (const g of groups) {
            if (g && g.id != null) {
              groupTitleById[Number(g.id)] = g.title ?? g.name ?? g.code ?? (`#${g.id}`);
            }
          }
        }
        return options.map(o => {
          const gid = (o && o.group != null) ? Number(o.group) : null;
          const group_title = (gid && groupTitleById[gid]) ? groupTitleById[gid] : undefined;
          return group_title ? { ...o, group_title } : o;
        });
      }

      const legacyEndpoints = [
        "/api/catalog/engineering_systems/",
        "/api/catalog/engineering-systems/",
        "/api/catalog/engineering/",
        "/api/catalog/engineeringsystems/",
      ];

      for (const url of legacyEndpoints) {
        const list = await tryGetList(url);
        if (list && list.length) return list;
      }

      return [];
    },

    // Orders
    async listOrders() {
      const res = await apiFetch("/api/orders/orders/", { method: "GET" });
      await ensureOk(res);
      const data = await res.json();
      return data.results || data;
    },

    async getOrder(id) {
      const res = await apiFetch(`/api/orders/orders/${id}/`, { method: "GET" });
      await ensureOk(res);
      return res.json();
    },

    async getOrderHistory(id) {
      const res = await apiFetch(`/api/orders/orders/${id}/history/`, { method: "GET" });
      await ensureOk(res);
      return res.json();
    },

    async changeOrderStatus(id, status) {
      const res = await apiFetch(`/api/orders/orders/${id}/change_status/`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      await ensureOk(res);
      return res.json();
    },
  };

  // expose globals
  window.DiplomAuth = { login, register, logout, ensureAccessToken };
  window.DiplomAPI = DiplomAPI;
})();
