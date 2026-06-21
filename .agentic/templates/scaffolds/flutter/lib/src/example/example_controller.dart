import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'example_model.dart';
import 'example_repository.dart';

/// The controller holds state as AsyncValue (loading | data | error) — the UI only renders
/// the state, it doesn't know HTTP. Canonical Riverpod pattern of one vertical slice.
class ExampleController extends AsyncNotifier<List<ExampleItem>> {
  @override
  Future<List<ExampleItem>> build() =>
      ref.watch(exampleRepositoryProvider).list();

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(exampleRepositoryProvider).list(),
    );
  }
}

final exampleControllerProvider =
    AsyncNotifierProvider<ExampleController, List<ExampleItem>>(
      ExampleController.new,
    );
