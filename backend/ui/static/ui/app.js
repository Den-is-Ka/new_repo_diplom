// --- Tiny JWT client for Diplom UI ---
(() => {
  const API_BASE = () => (window.DIPLOM && window.DIPLOM.API_BASE) ? window.DIPLOM.API_BASE : "";

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

  async function apiFetch(url, opts = {}) {
    const headers = new Headers(opts.headers || {});
    headers.set("Accept", "application/json");
    if (!headers.has("Content-Type") && opts.body) headers.set("Content-Type", "application/json");

    const access = getAccess();
    if (access) headers.set("Authorization", "Bearer " + access);

    const res = await rawFetch(url, { ...opts, headers });

    if (res.status !== 401) return res;

    // Try refresh
    const refreshed = await refreshToken();
    if (!refreshed) return res;

    const headers2 = new Headers(opts.headers || {});
    headers2.set("Accept", "application/json");
    if (!headers2.has("Content-Type") && opts.body) headers2.set("Content-Type", "application/json");
    headers2.set("Authorization", "Bearer " + getAccess());

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

  async function ensureAccessToken() {
    const a = getAccess();
    if (a) return true;
    return refreshToken();
  }

  function logout() { clearTokens(); }

  // --- Diplom API wrappers ---
  const DiplomAPI = {
    // Categories
    async getMainCategories() {
      const res = await apiFetch("/api/configurator/configurations/main_categories/", { method: "GET" });
      await ensureOk(res);
      return res.json();
    },

    // ✅ FIX: sub_categories у тебя принимает main_category_id=INT (а не main_category=...)
    async getSubCategories(mainId) {
      const tries = [
        `/api/configurator/configurations/sub_categories/?main_category_id=${encodeURIComponent(mainId)}`,
        `/api/configurator/configurations/sub_categories/?parent=${encodeURIComponent(mainId)}`,
      ];

      for (const url of tries) {
        const r = await apiFetch(url, { method: "GET" });
        if (r.ok) {
          const data = await r.json();
          return data.results || data;
        }
      }

      // если оба не подошли — вернём пусто (не будем делать 400-спам запросами)
      return [];
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

    async patchConfigurationModules(id, items) {
      const shapes = [
        { module_items: items },
        { modules: items },
        { items: items },
      ];

      let lastErr = null;
      for (const shape of shapes) {
        try {
          return await this.patchConfiguration(id, shape);
        } catch (e) {
          lastErr = e;
        }
      }
      throw lastErr || new Error("Failed to patch modules");
    },

    // ✅ FIX: available_modules у тебя требует category_id
    async getAvailableModules(categoryId) {
      const tries = [
        `/api/configurator/configurations/available_modules/?category_id=${encodeURIComponent(categoryId)}`,
        // запасные варианты (если потом поменяешь API)
        `/api/configurator/configurations/available_modules/?sub_category_id=${encodeURIComponent(categoryId)}`,
        `/api/configurator/configurations/available_modules/?sub_category=${encodeURIComponent(categoryId)}`,
      ];

      for (const url of tries) {
        const res = await apiFetch(url, { method: "GET" });
        if (res.ok) return res.json();
      }

      // fallback
      const res = await apiFetch("/api/configurator/configurations/available_modules/", { method: "GET" });
      await ensureOk(res);
      return res.json();
    },

    async setEngineering(cfgId, engineeringIds) {
      const res = await apiFetch(`/api/configurator/configurations/${cfgId}/set_engineering/`, {
        method: "POST",
        body: JSON.stringify({ engineering_systems: engineeringIds, engineering: engineeringIds, ids: engineeringIds }),
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

    // Engineering list (catalog)
    async getEngineeringList() {
      const ENGINEERING_ENDPOINTS = [
        "/api/catalog/engineering_systems/",
        "/api/catalog/engineering-systems/",
        "/api/catalog/engineering/",
        "/api/catalog/engineeringsystems/",
      ];
      for (const url of ENGINEERING_ENDPOINTS) {
        try {
          const res = await apiFetch(url, { method: "GET" });
          if (!res.ok) continue;
          const data = await res.json();
          return data.results || data;
        } catch {}
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
  window.DiplomAuth = { login, logout, ensureAccessToken };
  window.DiplomAPI = DiplomAPI;
})();