import argparse
import json
import os
import statistics
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*fixed sampling defaults.*")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_tutoring_system.settings")

import django

django.setup()

from django.conf import settings

from AI.rag_service import material_scope
from AI.vector_store import get_vector_store

IN_SCOPE_QUERIES = [
    "cấu trúc câu bị động trong tiếng Anh dùng thế nào",
    "khi nào dùng to V khi nào dùng V-ing",
    "cách viết lại câu với so that và such that",
    "câu điều kiện loại 2 dùng khi nào",
    "từ đồng nghĩa của important là gì",
    "cách dùng thì hiện tại hoàn thành",
    "mệnh đề quan hệ rút gọn là gì",
    "một số từ vựng chủ đề môi trường",
    "cấu trúc used to và be used to khác nhau ra sao",
    "câu tường thuật đổi thì như thế nào",
    "cấu trúc wish dùng để làm gì",
    "cách dùng mạo từ a an the",
    "các cấu trúc hay ra trong đề thi tốt nghiệp",
    "phân biệt say tell speak talk",
    "từ vựng về nghề nghiệp trong sách tiếng Anh 12",
]

OUT_OF_SCOPE_QUERIES = [
    "cách giải phương trình bậc hai",
    "định luật bảo toàn năng lượng phát biểu thế nào",
    "công thức tính đạo hàm của hàm hợp",
    "kể cho mình một chuyện cười",
    "hôm nay thời tiết thế nào",
    "cách nấu phở bò ngon",
    "ai là người sáng lập Facebook",
    "bảng tuần hoàn hóa học có bao nhiêu nguyên tố",
    "chiến dịch Điện Biên Phủ diễn ra năm nào",
    "cách cài đặt Windows 11",
    "tính diện tích hình tròn bán kính 5cm",
    "cho mình xin số điện thoại của giáo viên",
]

RECORD_TOP_K = 10
SWEEP_START = 0.20
SWEEP_STOP = 0.46
SWEEP_STEP = 0.01
LINE = "-" * 74


def log(message=""):
    print(message, flush=True)


def cache_path():
    return Path(settings.RAG_CACHE_DIR) / "threshold_eval.json"


def collect_distances():
    store = get_vector_store()
    scope = material_scope()
    records = []

    labelled = [(query, True) for query in IN_SCOPE_QUERIES]
    labelled += [(query, False) for query in OUT_OF_SCOPE_QUERIES]

    for order, (query, in_scope) in enumerate(labelled, start=1):
        found = store.similarity_search_with_score(query, k=RECORD_TOP_K, filter=scope)
        distances = [round(float(distance), 6) for _, distance in found]
        titles = [document.metadata.get("title", "") for document, _ in found]

        log(f"  [{order}/{len(labelled)}] {query[:52]:<52} {min(distances):.4f}")
        records.append(
            {
                "query": query,
                "in_scope": in_scope,
                "distances": distances,
                "nearest_title": titles[0] if titles else "",
            }
        )

    return records


def load_records(refresh):
    path = cache_path()

    if not refresh and path.exists():
        log(f"Đọc lại kết quả đã đo từ {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    log(f"Đo khoảng cách cho {len(IN_SCOPE_QUERIES) + len(OUT_OF_SCOPE_QUERIES)} câu hỏi")
    log("Mỗi câu tốn một lượt gọi API tạo vector")
    log(LINE)
    records = collect_distances()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(LINE)
    log(f"Đã lưu dữ liệu thô vào {path}")
    return records


def describe_group(records, in_scope):
    values = [
        min(record["distances"]) for record in records if record["in_scope"] == in_scope
    ]
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
    }


def score_threshold(records, threshold):
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0

    for record in records:
        retrieved_something = min(record["distances"]) <= threshold

        if record["in_scope"] and retrieved_something:
            true_positive += 1
        elif record["in_scope"] and not retrieved_something:
            false_negative += 1
        elif not record["in_scope"] and retrieved_something:
            false_positive += 1
        else:
            true_negative += 1

    predicted_positive = true_positive + false_positive
    actual_positive = true_positive + false_negative

    precision = true_positive / predicted_positive if predicted_positive else 0.0
    recall = true_positive / actual_positive if actual_positive else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "threshold": threshold,
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "tn": true_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def sweep(records):
    rows = []
    threshold = SWEEP_START
    while threshold <= SWEEP_STOP + 1e-9:
        rows.append(score_threshold(records, round(threshold, 4)))
        threshold += SWEEP_STEP
    return rows


def best_plateau(rows):
    best_f1 = max(row["f1"] for row in rows)
    winners = [row["threshold"] for row in rows if row["f1"] == best_f1]

    plateau = [winners[0]]
    for value in winners[1:]:
        if round(value - plateau[-1], 4) <= SWEEP_STEP + 1e-9:
            plateau.append(value)
        else:
            break

    return best_f1, plateau[0], plateau[-1]


def report(records, rows, current_threshold):
    in_scope = describe_group(records, True)
    out_scope = describe_group(records, False)

    log()
    log("PHÂN BỐ KHOẢNG CÁCH GẦN NHẤT THEO TỪNG NHÓM CÂU HỎI")
    log(LINE)
    log(f"{'Nhóm câu hỏi':<34}{'Số câu':>8}{'Nhỏ nhất':>11}{'Lớn nhất':>11}{'Trung bình':>12}")
    log(
        f"{'Thuộc phạm vi kho tài liệu':<34}{in_scope['count']:>8}"
        f"{in_scope['min']:>11.4f}{in_scope['max']:>11.4f}{in_scope['mean']:>12.4f}"
    )
    log(
        f"{'Ngoài phạm vi kho tài liệu':<34}{out_scope['count']:>8}"
        f"{out_scope['min']:>11.4f}{out_scope['max']:>11.4f}{out_scope['mean']:>12.4f}"
    )

    gap = out_scope["min"] - in_scope["max"]
    log()
    if gap > 0:
        log(f"Khoảng trống giữa hai nhóm: {in_scope['max']:.4f} → {out_scope['min']:.4f} (rộng {gap:.4f})")
    else:
        log("Hai nhóm chồng lấn nhau, không có khoảng trống nào tách bạch")

    log()
    log("QUÉT NGƯỠNG")
    log(LINE)
    log(
        f"{'Cosine':>8}{'L2 tương đương':>16}{'TP':>5}{'FP':>5}{'FN':>5}{'TN':>5}"
        f"{'Precision':>12}{'Recall':>9}{'F1':>8}"
    )

    best_f1, plateau_low, plateau_high = best_plateau(rows)

    for row in rows:
        mark = ""
        if abs(row["threshold"] - current_threshold) < 1e-9:
            mark = "  <- đang dùng"
        elif row["f1"] == best_f1:
            mark = "  *"

        log(
            f"{row['threshold']:>8.2f}{row['threshold'] * 2:>16.2f}"
            f"{row['tp']:>5}{row['fp']:>5}{row['fn']:>5}{row['tn']:>5}"
            f"{row['precision']:>12.3f}{row['recall']:>9.3f}{row['f1']:>8.3f}{mark}"
        )

    midpoint = round((plateau_low + plateau_high) / 2, 3)

    log()
    log("KẾT LUẬN")
    log(LINE)
    log(f"F1 cao nhất: {best_f1:.3f}")
    log(f"Đạt được trên toàn dải ngưỡng cosine từ {plateau_low:.2f} đến {plateau_high:.2f}")
    log(f"Điểm giữa của dải: {midpoint:.3f} cosine, tương đương {midpoint * 2:.3f} theo thang L2")
    log(f"Giá trị RAG_MAX_DISTANCE đang cấu hình: {current_threshold}")

    current_row = min(rows, key=lambda row: abs(row["threshold"] - current_threshold))
    log(
        f"Tại ngưỡng đang cấu hình: precision {current_row['precision']:.3f}, "
        f"recall {current_row['recall']:.3f}, F1 {current_row['f1']:.3f}"
    )

    log()
    log("GIỚI HẠN CỦA THỰC NGHIỆM")
    log(LINE)
    log(f"Tập đánh giá gồm {len(records)} câu hỏi do người làm đồ án tự soạn và tự gán nhãn.")
    log("Kho tài liệu hiện chỉ có môn Tiếng Anh khối 12, nên kết quả chưa suy rộng")
    log("được cho các môn khác. Nạp thêm tài liệu môn mới thì phải chạy lại phép đo này.")


def run_cli():
    parser = argparse.ArgumentParser(
        description="Đo precision, recall, F1 của ngưỡng lọc khoảng cách trong truy hồi RAG"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Đo lại khoảng cách bằng cách gọi API, thay vì dùng dữ liệu đã lưu",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=settings.RAG_MAX_DISTANCE,
        help="Ngưỡng cần đánh dấu trong bảng, mặc định lấy từ cấu hình hệ thống",
    )
    args = parser.parse_args()

    records = load_records(args.refresh)
    report(records, sweep(records), args.threshold)


if __name__ == "__main__":
    run_cli()
