import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

// form_model — canonical write binding (rules/frontend.md §Form model).
// ONE central model = single source of truth for data/errors/touched/submitting/dirty.
// Validation = dry-run of the same persistence operation (rules §Write-flow). The UI binds
// to a field via a thin FormFieldBinding that does not know the storage mechanics.
//
// ChangeNotifier = no extra dependencies; in Riverpod wrap with
// `ChangeNotifierProvider.autoDispose`. The editable subtree is `Map<String, Object?>`
// = write payload (`*Data`); readonly context from `*ExtData` is held by the page separately.

@immutable
class FormModelState {
  const FormModelState({
    required this.data,
    this.errors = const {},
    this.touched = const {},
    this.submitting = false,
    this.loading = false,
    this.globalError,
  });

  final Map<String, Object?> data;
  final Map<String, String> errors;
  final Set<String> touched;
  final bool submitting;
  final bool loading;
  final String? globalError;

  FormModelState copyWith({
    Map<String, Object?>? data,
    Map<String, String>? errors,
    Set<String>? touched,
    bool? submitting,
    bool? loading,
    String? globalError,
    bool clearGlobalError = false,
  }) {
    return FormModelState(
      data: data ?? this.data,
      errors: errors ?? this.errors,
      touched: touched ?? this.touched,
      submitting: submitting ?? this.submitting,
      loading: loading ?? this.loading,
      globalError: clearGlobalError ? null : (globalError ?? this.globalError),
    );
  }
}

/// Result of the persistence operation. fieldErrors = field-level; error = global/throw.
class SaveResult {
  const SaveResult({this.fieldErrors = const {}, this.error});
  final Map<String, String> fieldErrors;
  final Object? error;
}

/// Thin field abstraction — the widget knows only this, not the storage.
class FormFieldBinding<T> {
  const FormFieldBinding({
    required this.value,
    required this.set,
    required this.blur,
    required this.error,
  });
  final T value;
  final void Function(T value) set;
  final VoidCallback blur;
  final String? error;
}

/// validate=true → dry-run (server ONLY validates, no side effects); false → commit.
typedef SaveFn =
    Future<SaveResult> Function(Map<String, Object?> data, bool validate);

class FormModelController extends ChangeNotifier {
  FormModelController({
    required Map<String, Object?> defaultData,
    required SaveFn save,
    Future<Map<String, Object?>> Function()? load,
    void Function(Map<String, Object?> data)? onSuccess,
    this.debounce = const Duration(milliseconds: 400),
  }) : _save = save,
       _load = load,
       _onSuccess = onSuccess,
       _state = FormModelState(data: Map.of(defaultData)),
       _baseline = jsonEncode(defaultData);

  final SaveFn _save;
  final Future<Map<String, Object?>> Function()? _load;
  final void Function(Map<String, Object?> data)? _onSuccess;
  final Duration debounce;

  FormModelState _state;
  FormModelState get state => _state;
  String _baseline;
  Timer? _timer;

  bool get isDirty => jsonEncode(_state.data) != _baseline;

  void _emit(FormModelState s) {
    _state = s;
    notifyListeners();
  }

  FormFieldBinding<T> field<T>(String key) {
    return FormFieldBinding<T>(
      value: _state.data[key] as T,
      set: (value) {
        _emit(_state.copyWith(data: {..._state.data, key: value}));
        _scheduleValidate();
      },
      blur: () {
        _timer?.cancel();
        _emit(_state.copyWith(touched: {..._state.touched, key}));
        unawaited(_validate());
      },
      error: _state.touched.contains(key) ? _state.errors[key] : null,
    );
  }

  void _scheduleValidate() {
    _timer?.cancel();
    _timer = Timer(debounce, () => unawaited(_validate()));
  }

  Future<bool> _validate() async {
    final r = await _save(_state.data, true);
    _emit(_state.copyWith(errors: r.fieldErrors));
    return r.fieldErrors.isEmpty;
  }

  Future<void> submit() async {
    _timer?.cancel();
    _emit(_state.copyWith(submitting: true, clearGlobalError: true));
    try {
      if (!await _validate()) {
        return; // dry-run stops the commit
      }
      final r = await _save(_state.data, false);
      if (r.fieldErrors.isNotEmpty) {
        _emit(_state.copyWith(errors: r.fieldErrors));
        return;
      }
      if (r.error != null) {
        _emit(_state.copyWith(globalError: 'common.error'));
        return;
      }
      _baseline = jsonEncode(_state.data);
      _onSuccess?.call(_state.data);
    } finally {
      _emit(_state.copyWith(submitting: false));
    }
  }

  Future<void> loadInitial() async {
    final load = _load;
    if (load == null) {
      return;
    }
    _emit(_state.copyWith(loading: true));
    try {
      final data = await load();
      _baseline = jsonEncode(data);
      _emit(_state.copyWith(data: data, loading: false));
    } catch (_) {
      _emit(_state.copyWith(loading: false));
      rethrow;
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
