def only_published(query, *ancestor_paths):
    """Lọc queryset xuống phần đã công khai.

    ``ancestor_paths`` là các đường dẫn quan hệ tới cấp cha cũng cần công khai,
    ví dụ ``only_published(resources, "lesson", "lesson__chapter")``.
    """
    lookups = {"published_at__isnull": False}
    for path in ancestor_paths:
        lookups[f"{path}__published_at__isnull"] = False
    return query.filter(**lookups)
