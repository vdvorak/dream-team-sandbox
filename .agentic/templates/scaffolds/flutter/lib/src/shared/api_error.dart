/// Canonical API error shape — mirrors the backend `{code, details}`
/// (python/java scaffold `ApiError`). The client never guesses the error structure:
/// `code` is a stable machine string, `details` an optional structure.
class ApiError implements Exception {
  const ApiError({required this.code, this.details});

  final String code;
  final Map<String, Object?>? details;

  factory ApiError.fromJson(Map<String, Object?> json) => ApiError(
    code: json['code'] as String? ?? 'unknown',
    details: json['details'] as Map<String, Object?>?,
  );

  @override
  String toString() => 'ApiError(code: $code, details: $details)';
}
