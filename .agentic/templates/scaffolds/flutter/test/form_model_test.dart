import 'package:flutter_test/flutter_test.dart';

import 'package:app/src/shared/form_model.dart';

void main() {
  test('submit: dry-run validate → commit when clean', () async {
    final calls = <bool>[];
    final controller = FormModelController(
      defaultData: {'label': ''},
      save: (data, validate) async {
        calls.add(validate);
        return const SaveResult();
      },
    );

    controller.field<String>('label').set('hi');
    await controller.submit();

    expect(calls, [true, false]); // validation-only, then commit
    expect(controller.state.data['label'], 'hi');
  });

  test('submit: field error from dry-run stops commit', () async {
    final calls = <bool>[];
    final controller = FormModelController(
      defaultData: {'label': ''},
      save: (data, validate) async {
        calls.add(validate);
        return const SaveResult(fieldErrors: {'label': 'required'});
      },
    );

    await controller.submit();

    expect(calls, [true]); // only validation-only; no commit
  });
}
