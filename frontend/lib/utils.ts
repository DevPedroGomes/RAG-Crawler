import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Get cookie value by name
 * @param name - Cookie name
 * @returns Cookie value or empty string
 */
export function getCookie(name: string): string {
  if (typeof document === 'undefined') return ''

  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)

  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || ''
  }

  return ''
}

/**
 * Get CSRF token from XSRF-TOKEN cookie
 * @returns CSRF token
 */
export function getCSRFToken(): string {
  return getCookie('XSRF-TOKEN')
}
