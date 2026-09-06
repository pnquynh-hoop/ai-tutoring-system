import logging
from celery import shared_task
from academics.models import Material
from courses.models import LearningResource
from .ingest import ingest_material, ingest_resource

logger = logging.getLogger(__name__)


@shared_task(name="AI.ingest_resource")
def ingest_resource_task(resource_id):
    resource = (
        LearningResource.objects.select_related("lesson__chapter__course")
        .filter(pk=resource_id)
        .first()
    )

    if resource is None:
        logger.warning("Không tìm thấy LearningResource ID %s để nạp", resource_id)
        return 0

    return ingest_resource(resource)


@shared_task(name="AI.ingest_material")
def ingest_material_task(material_id):
    material = (
        Material.objects.select_related("subject", "grade").filter(pk=material_id).first()
    )

    if material is None:
        logger.warning("Không tìm thấy Material ID %s để nạp", material_id)
        return 0

    return ingest_material(material)
