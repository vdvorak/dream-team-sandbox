import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:app/src/example/example_model.dart';
import 'package:app/src/example/example_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  test('list() maps the JSON response to ExampleItem models', () async {
    final dio = _MockDio();
    when(() => dio.get<List<Object?>>('/api/examples')).thenAnswer(
      (_) async => Response<List<Object?>>(
        requestOptions: RequestOptions(path: '/api/examples'),
        data: const [
          {'id': 1, 'name': 'Alpha'},
          {'id': 2, 'name': 'Beta'},
        ],
      ),
    );

    final repo = ExampleRepository(dio);
    final items = await repo.list();

    expect(items, hasLength(2));
    expect(items.first, const ExampleItem(id: 1, name: 'Alpha'));
    expect(items.last.name, 'Beta');
  });
}
