import { getCookie } from "./utils"

/**
 * Check if user is authenticated by checking if session cookie exists
 * @returns true if authenticated
 */
export const isAuthenticated = (): boolean => {
  return getCookie('sid') !== ''
}

/**
 * @deprecated No longer needed - cookies are managed by the backend
 * This function is kept for backwards compatibility but does nothing
 */
export const setToken = (_token: string) => {
  // Cookies are now set automatically by the backend
  // This function is kept for backwards compatibility
}

/**
 * @deprecated No longer needed - cookies are managed by the backend
 * This function is kept for backwards compatibility but returns empty string
 */
export const getToken = (): string | null => {
  // Tokens are no longer stored in localStorage
  // Authentication is handled via HttpOnly cookies
  return null
}

/**
 * @deprecated No longer needed - cookies are cleared by the backend on logout
 * This function is kept for backwards compatibility but does nothing
 */
export const clearToken = () => {
  // Cookies are cleared by the backend on logout
  // This function is kept for backwards compatibility
}
