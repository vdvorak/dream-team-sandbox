/// Domain model of a single item.
///
/// Plain immutable Dart (no `freezed` codegen) — the skeleton is turnkey buildable
/// without a `build_runner` step. `freezed`/`json_serializable` are vetted capabilities
/// (recommended-libs `flutter`), not mandatory; reach for them when models grow.
class ExampleItem {
  const ExampleItem({required this.id, required this.name});

  final int id;
  final String name;

  factory ExampleItem.fromJson(Map<String, Object?> json) => ExampleItem(
    id: (json['id'] as num).toInt(),
    name: json['name'] as String,
  );

  Map<String, Object?> toJson() => {'id': id, 'name': name};

  ExampleItem copyWith({int? id, String? name}) =>
      ExampleItem(id: id ?? this.id, name: name ?? this.name);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ExampleItem && other.id == id && other.name == name;

  @override
  int get hashCode => Object.hash(id, name);
}
