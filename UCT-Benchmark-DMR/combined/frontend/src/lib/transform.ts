/**
 * Generic key transformation utilities for backend/frontend data conversion.
 *
 * The backend uses snake_case naming while the frontend uses camelCase.
 * These utilities help convert between the two conventions.
 */

/**
 * Convert a snake_case string to camelCase.
 *
 * @param str - String in snake_case format
 * @returns String in camelCase format
 *
 * @example
 * snakeToCamel('created_at') // 'createdAt'
 * snakeToCamel('f1_score') // 'f1Score'
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

/**
 * Convert a camelCase string to snake_case.
 *
 * @param str - String in camelCase format
 * @returns String in snake_case format
 *
 * @example
 * camelToSnake('createdAt') // 'created_at'
 * camelToSnake('f1Score') // 'f1_score'
 */
export function camelToSnake(str: string): string {
  return str.replace(/([A-Z])/g, (c) => `_${c.toLowerCase()}`);
}

/**
 * Transform all keys in an object from snake_case to camelCase.
 *
 * @param obj - Object with snake_case keys
 * @returns New object with camelCase keys
 *
 * @example
 * transformKeys({ created_at: '2025-01-01', f1_score: 0.95 })
 * // { createdAt: '2025-01-01', f1Score: 0.95 }
 */
export function transformKeys<T extends Record<string, unknown>>(
  obj: Record<string, unknown>
): T {
  return Object.fromEntries(
    Object.entries(obj).map(([key, value]) => [snakeToCamel(key), value])
  ) as T;
}

/**
 * Transform all keys in an object from camelCase to snake_case.
 *
 * @param obj - Object with camelCase keys
 * @returns New object with snake_case keys
 *
 * @example
 * transformKeysToSnake({ createdAt: '2025-01-01', f1Score: 0.95 })
 * // { created_at: '2025-01-01', f1_score: 0.95 }
 */
export function transformKeysToSnake<T extends Record<string, unknown>>(
  obj: Record<string, unknown>
): T {
  return Object.fromEntries(
    Object.entries(obj).map(([key, value]) => [camelToSnake(key), value])
  ) as T;
}

/**
 * Transform an array of objects from snake_case to camelCase keys.
 *
 * @param arr - Array of objects with snake_case keys
 * @returns New array with camelCase keys
 */
export function transformArrayKeys<T extends Record<string, unknown>>(
  arr: Record<string, unknown>[]
): T[] {
  return arr.map((item) => transformKeys<T>(item));
}
