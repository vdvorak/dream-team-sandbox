import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_error.dart';

/// API base URL. The project overrides it at build time: `--dart-define=API_BASE_URL=…`.
const String _apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

/// Shared HTTP client. The interceptor maps error responses of the shape `{code, details}`
/// to a typed [ApiError] — higher layers catch a domain error, not raw Dio.
Dio createApiClient() {
  final dio = Dio(
    BaseOptions(
      baseUrl: _apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ),
  );
  dio.interceptors.add(
    InterceptorsWrapper(
      onError: (e, handler) {
        final data = e.response?.data;
        if (data is Map<String, Object?> && data['code'] != null) {
          handler.reject(
            DioException(
              requestOptions: e.requestOptions,
              response: e.response,
              type: e.type,
              error: ApiError.fromJson(data),
            ),
          );
        } else {
          handler.next(e);
        }
      },
    ),
  );
  return dio;
}

/// Client provider — injectable (a test overrides it with a mock via overrides).
final apiClientProvider = Provider<Dio>((ref) => createApiClient());
