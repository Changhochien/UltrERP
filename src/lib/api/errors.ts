/**
 * API Error types and utilities.
 */

export interface ApiErrorDetail {
  errors?: Array<{ field?: string; message: string }>;
  message?: string;
}

/**
 * API Error class for handling API errors consistently.
 */
export class ApiError extends Error {
  status: number;
  detail: ApiErrorDetail | string;

  constructor(status: number, detail: ApiErrorDetail | string) {
    super(typeof detail === "string" ? detail : detail.message ?? "An error occurred");
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  static async fromResponse(response: Response): Promise<ApiError> {
    let detail: ApiErrorDetail | string;
    const contentType = response.headers.get("content-type");

    if (contentType?.includes("application/json")) {
      const body = await response.json();
      detail = body.detail ?? body;
    } else {
      detail = await response.text();
    }

    return new ApiError(response.status, detail);
  }
}
