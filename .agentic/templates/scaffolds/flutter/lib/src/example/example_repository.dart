import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../shared/api_client.dart';
import 'example_model.dart';

/// Repository = the only place this domain touches the API. Returns typed models;
/// errors propagate as [ApiError] (mapped by the api_client interceptor).
class ExampleRepository {
  ExampleRepository(this._dio);
  final Dio _dio;

  Future<List<ExampleItem>> list() async {
    final res = await _dio.get<List<Object?>>('/api/examples');
    final data = res.data ?? const [];
    return data
        .cast<Map<String, Object?>>()
        .map(ExampleItem.fromJson)
        .toList(growable: false);
  }
}

final exampleRepositoryProvider = Provider<ExampleRepository>(
  (ref) => ExampleRepository(ref.watch(apiClientProvider)),
);
