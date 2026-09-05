let csrfToken = null;

export function getCsrfToken() {
    return csrfToken;
}

export function setCsrfToken(token) {
    csrfToken = token || null;
}

export function clearCsrfToken() {
    csrfToken = null;
}

export async function fetchCsrfToken(api) {
    const response = await api.get("/api/v1/auth/csrf");
    setCsrfToken(response.data?.csrf_token);
    return csrfToken;
}
