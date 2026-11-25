"""Prevention layer: every field of every registered action must have a label.

This runs when the app loads the registered actions (see ``ext``), not in
``AuditLogSchema.__init_subclass__``: marshmallow only sets a schema's fields
after ``__init_subclass__`` has run, so they can't be read there.
"""

from marshmallow import fields

LABELS = ("ref", "scrub", "keep")


def collect_labels(schema, prefix=""):
    """Return the label of every leaf field, and the errors found.

    List items get ``[]`` in their path. For example, for the grant action:
        labels = {"user.email": "scrub", "metadata.after[].subject.id": "ref", ...}
        errors = []
    """
    labels = {}
    errors = []

    for name, field in schema.fields.items():
        path = prefix + name

        # Containers have no label of their own: look inside them.
        if isinstance(field, fields.Nested):
            inner_labels, inner_errors = collect_labels(field.schema, path + ".")
            labels.update(inner_labels)
            errors.extend(inner_errors)
            continue

        if isinstance(field, fields.List) and isinstance(field.inner, fields.Nested):
            inner_labels, inner_errors = collect_labels(field.inner.schema, path + "[].")
            labels.update(inner_labels)
            errors.extend(inner_errors)
            continue

        # A leaf field, or a List/Dict/Raw that is labelled as one blob.
        label = field.metadata.get("user_data")
        if label is None:
            errors.append(f"{path}: missing metadata={{'user_data': ...}}")
            continue
        if label not in LABELS:
            errors.append(f"{path}: unknown label {label!r}, use one of {LABELS}")
            continue

        # The deletion SQL removes JSON paths. A path inside a list would need
        # one path per item, which it can't build yet.
        if label == "scrub" and "[]" in path:
            errors.append(f"{path}: 'scrub' inside a list is not supported yet")
            continue

        labels[path] = label

    return labels, errors


def check_registered_actions(registered_actions):
    """Return the labels of every registered action, or raise if any field is unlabelled.

    For example:
        {"post.create": {"user.email": "scrub", "metadata.title": "keep", ...}, ...}
    """
    labels_by_action = {}
    all_errors = []

    for action_id, action_cls in sorted(registered_actions.items()):
        schema = action_cls.marshmallow_schema()()
        labels, errors = collect_labels(schema)

        labels_by_action[action_id] = labels
        for error in errors:
            all_errors.append(f"{action_id}: {error}")

    if all_errors:
        raise TypeError("Unlabelled audit log data:\n " + "\n ".join(all_errors))

    return labels_by_action
