from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.product import ProductVariant
from app.models.user import User
from app.permissions import PRODUCT_READ
from app.schemas.label import LabelPreviewRequest
from app.services.barcode_gen import code128_svg_data_uri

router = APIRouter(prefix="/labels", tags=["labels"])


def _attributes(variant: ProductVariant) -> dict:
    attrs = {
        "size": variant.attribute_size,
        "color": variant.attribute_color,
        "thickness": variant.attribute_thickness,
        "type": variant.attribute_type,
        "packaging": variant.attribute_packaging,
    }
    return {key: value for key, value in attrs.items() if value}


@router.post("/preview")
def preview_labels(
    payload: LabelPreviewRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRODUCT_READ)),
):
    if not payload.items:
        raise BusinessRuleError("Pilih minimal satu varian.", code="NO_ITEMS")

    labels = []
    for item in payload.items:
        variant = db.get(ProductVariant, item.variant_id)
        if variant is None:
            raise NotFoundError("Varian tidak ditemukan.")
        code = variant.barcode or variant.sku
        labels.append(
            {
                "variant_id": str(variant.id),
                "product_name": variant.product.name,
                "sku": variant.sku,
                "barcode": variant.barcode,
                "code": code,
                "has_barcode": variant.barcode is not None,
                "attributes": _attributes(variant),
                "barcode_svg": code128_svg_data_uri(code),
                "copies": item.copies,
            }
        )
    return {"template": payload.template, "total": len(labels), "labels": labels}
