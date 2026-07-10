"""Canonical human labels for schema fields shown to staff."""

from __future__ import annotations

FIELD_LABELS = {
    "buyer_name": "Buyer name",
    "buyer_email": "Buyer email",
    "buyer_phone": "Buyer phone",
    "vendor_name": "Seller name",
    "vendor_email": "Seller email",
    "vendor_phone": "Seller phone",
    "buyer_solicitor_name": "Buyer solicitor name",
    "buyer_solicitor_firm": "Buyer solicitor firm",
    "buyer_solicitor_email": "Buyer solicitor email",
    "buyer_solicitor_phone": "Buyer solicitor phone",
    "seller_solicitor_name": "Seller solicitor name",
    "seller_solicitor_firm": "Seller solicitor firm",
    "seller_solicitor_email": "Seller solicitor email",
    "seller_solicitor_phone": "Seller solicitor phone",
    "sale_price": "Sale price",
    "chain_links": "Chain details",
}


def label_for_field(field_name: str) -> str:
    """Return a stable staff-facing label for a schema field or gate message."""
    field = (field_name or "").strip()
    if not field:
        return ""
    if field.startswith("incomplete chain"):
        return "Chain details"
    return FIELD_LABELS.get(field, field.replace("_", " ").capitalize())


def labels_for_fields(field_names: list[str] | tuple[str, ...] | None) -> list[str]:
    """Convert field names to labels, dropping empty values and duplicates."""
    labels: list[str] = []
    seen: set[str] = set()
    for field_name in field_names or []:
        label = label_for_field(str(field_name))
        if label and label not in seen:
            labels.append(label)
            seen.add(label)
    return labels
