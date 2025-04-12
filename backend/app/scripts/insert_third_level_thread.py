import os
import json
import pathlib
import sys
from pathlib import Path
from datetime import datetime

# Add project root to sys.path to allow imports from app
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

from app.models.user import User
from app.core.security import get_password_hash
from app.models.thread import Thread
from app.models.category import Category
from app.models.post import Post
from sqlmodel import Session, update, select
from app.core.db import engine

from sqlalchemy.dialects.postgresql import insert

thread_mapping = {
    21: "lap-trinh-cntt",
    18: "tuyen-dung-tim-viec",
}

BATCH_SIZE = 500 # Process 500 records at a time

# Example data:
# {"message_id": "22601839", "user_name": "Fire Of Heart", "message_time": "2023-01-04T02:38:06+0700", "content": "Ngồi suy nghĩ tổ chức cái gì cho đông người tham gia mà không quá khó cho mọi người, cuối cùng cũng nảy ra dc 1 ý tưởng như sau: \nChia sẻ kinh nghiệm phỏng vấn. \n \nThể lệ như sau: \n \n Bạn kể lại ngay trong thread này về những lần phỏng vấn của bạn trong năm 2021-2022. \n Bắt buộc: Phải ghi rõ tên công ty. \n Càng chi tiết càng tốt. Đầy đủ từng vòng từ khâu nộp cv qua đâu, coding online, home work v.v... \n Kể lại đầy đủ những câu hỏi phỏng vấn trong lần phỏng vấn đó. Cách bạn trả lời như nào. \n Đúc rút kinh nghiệm sau lần phỏng vấn đó. Vì sao thành công, vì sao tạch, chỗ nào trả lời tốt, chỗ nào trả lời dở.  Cái này là quan trọng nhất. Ko quan trọng là bạn nhận dc offer hay ko, quan trọng là rút ra dc những bài học nào để tiến bộ hơn. Khuyến khích mọi ng tham gia bất kể số năm kinh nghiệm, vị trí, v.v... \n \nGiải thưởng: \n \n Dành cho những post nào nhiều lượt ưng nhất, có nội dung tốt nhất. Cái này mình sẽ lựa theo cảm tính 1 phần nữa, nói trc vậy luôn cho khỏi thắc mắc. \n Sẽ có giải thưởng cho 3-5 người, bao gồm tít (Chắc chắn có) + hiện vật (xin sau, có thể có hoặc ko). \n \nFormat mẫu cho các bạn tham gia: \n \n \n Công ty: ABC \n Thời điểm phỏng vấn: 07/2022 \n Nơi nộp CV: HR contact qua linkedin \n Chuẩn bị: Đã dành 2 tuần để cày 100 bài code thiếu nhi, system design ở trang abcxyz... \n Round 1: \n Là 1 bài home work ko quá khó, độ khó cỡ leetcode medium, làm trong 60 phút. \nDo mình chưa nắm kỹ về cấu trúc dữ liệu Abcxyz nên dính TLE. Sau khi hết thời gian mới ngồi research và tìm ra cách giải tối ưu với kỹ thuật xyz. \n- Round 2: \nPhỏng vấn online qua google hangout với 1 anh abc xyz. \nĐầu tiên 2 bên giới thiệu lẫn nhau như bình thường, ấn tượng đầu tiên là anh ấy có vẻ hơi khó tính và nghiêm túc. Câu hỏi đầu tiên là 1 câu về OOP, yêu cầu mình giải thích tính chất XYZ. bla bla bla \n- Round X: \nGặp CTO abc xyz , bla bla bla \n- Round N: \nHR gửi offer nhưng mình thấy quá thấp nên đã thảo luận và deal lại lương. Mình đã nói là mức offer này chỉ cao hơn 10% so với offer hiện tại và đang có offer khác tốt hơn. Mình rất thích cty vì môi trường và tính ứng dụng của sản phẩm nhưng lương thấp vậy thì khó. Sau khi nghe chia sẻ HR đã gửi lại offer với mức cao hơn. \n- Kinh nghiệm sau lần phỏng vấn: Đã không trả lời tốt ở câu xyz vì lý do abc. Do ôn kỹ phần system design nên trả lời tự tin v.v.... \n \n \nCơ bản là thế, các bạn cứ linh động ko gò bó template nhé. \n \nThế nhé, hy vọng là sẽ đông người tham gia. Một người chia sẻ thì ko có gì nhiều nhưng nếu 10-100 người cùng tham gia sẽ có 1 tập kinh nghiệm phỏng vấn chất lượng. Giống thread chia sẻ lương vậy. \n \n Các thím muốn đóng góp gì về nội dung event thì tạm thời có thể đăng ở thread này luôn cũng dc. Sau này thống nhất rồi thì mình sẽ xóa sau cho đỡ loãng.", "quotes": [], "user_id": 873787}

def get_user_id_map(db: Session, origin_user_ids: set[int]) -> dict[int, int]:
    """Queries the database for User IDs corresponding to a set of origin_user_ids."""
    if not origin_user_ids:
        return {}
    user_select_stmt = select(User.id, User.origin_user_id).where(User.origin_user_id.in_(origin_user_ids))
    results = db.exec(user_select_stmt).all()
    return {origin_id: db_id for db_id, origin_id in results}

def main():
    script_dir = Path(__file__).parent.absolute()
    data_dir = script_dir / "data"
    print(f"Using data directory: {data_dir}")

    for category_id, category_name in thread_mapping.items():
        base_dir = data_dir / category_name
        if not base_dir.exists():
            print(f"Directory {base_dir} does not exist")
            continue

        for third_level_dir in base_dir.iterdir():
            if not third_level_dir.is_dir() or third_level_dir.name.startswith("."):
                continue

            third_level_thread_name = third_level_dir.name
            data_file = third_level_dir / "data.json"
            if not data_file.exists():
                print(f"Data file not found: {data_file}")
                continue

            print(f"Processing file: {data_file}")
            thread_id = None
            first_user_origin_id = None

            try:
                with Session(engine) as db:
                    # --- Process First Line: Create Thread and First User --- 
                    try:
                        with open(data_file, "r", encoding="utf-8") as f:
                            first_line = f.readline()
                            if not first_line:
                                print(f"Skipping empty file: {data_file}")
                                continue # Skip empty file
                            data = json.loads(first_line)
                            first_user_origin_id = data["user_id"]
                            user_name = data["user_name"]
                            
                            # Insert/Get first user
                            first_user_q = insert(User).values(
                                user_name=user_name,
                                email=f"{first_user_origin_id}@gmail.com",
                                origin_user_id=first_user_origin_id,
                                hashed_password=get_password_hash("12345678"),
                            ).on_conflict_do_nothing(index_elements=["origin_user_id"])
                            db.execute(first_user_q) # Use execute for non-returning statement
                            db.commit() # Commit separately to ensure user exists before thread creation
                            
                            user_id_map = get_user_id_map(db, {first_user_origin_id})
                            db_user_id = user_id_map.get(first_user_origin_id)
                            
                            if db_user_id is None:
                                print(f"ERROR: Could not get DB ID for thread creator {first_user_origin_id} in {data_file}")
                                continue # Skip this file if creator can't be established
                                
                            # Create Thread
                            thread = Thread(
                                title=third_level_thread_name,
                                category_id=category_id,
                                user_id=db_user_id,
                                children_count=0, # Initialize count, will be updated in batches
                            )
                            db.add(thread)
                            db.commit()
                            db.refresh(thread)
                            thread_id = thread.id
                            print(f"Created thread ID: {thread_id} for {data_file}")

                            # Update category count
                            category_update_q = update(Category).values(children_count=Category.children_count + 1).where(Category.id == category_id)
                            db.execute(category_update_q)
                            db.commit()

                    except Exception as e:
                         print(f"Error processing first line of {data_file}: {e}")
                         continue # Skip to next file if first line fails
                    
                    # --- Process Remaining Lines in Batches --- 
                    batch_lines = []
                    total_posts_processed = 0
                    with open(data_file, "r", encoding="utf-8") as f:
                        f.readline() # Skip the first line again
                        for line in f:
                            batch_lines.append(line)
                            if len(batch_lines) >= BATCH_SIZE:
                                posts_in_batch = process_batch(db, batch_lines, thread_id)
                                total_posts_processed += posts_in_batch
                                print(f"  Processed batch of {posts_in_batch} posts for thread {thread_id}. Total: {total_posts_processed}")
                                batch_lines = [] # Reset batch
                        
                        # Process the final partial batch
                        if batch_lines:
                            posts_in_batch = process_batch(db, batch_lines, thread_id)
                            total_posts_processed += posts_in_batch
                            print(f"  Processed final batch of {posts_in_batch} posts for thread {thread_id}. Total: {total_posts_processed}")
                    
                    print(f"Finished processing {data_file}. Total posts: {total_posts_processed}")
            
            except Exception as e:
                print(f"FATAL ERROR processing file {data_file}: {e}")
                # Decide if you want to continue with the next file or stop

def process_batch(db: Session, batch_lines: list[str], thread_id: int) -> int:
    """Processes a batch of lines: inserts users, maps IDs, inserts posts, updates count."""
    if not batch_lines:
        return 0

    users_in_batch = {} # {origin_id: user_name}
    posts_data = []     # List of dicts for post insertion
    valid_lines_in_batch = 0

    for line in batch_lines:
        try:
            data = json.loads(line)
            origin_user_id = data["user_id"]
            user_name = data["user_name"]
            message_time = data["message_time"]
            content = data["content"]
            # quotes = data["quotes"] # Assuming quotes are handled differently or not needed now
            
            # Collect unique users for batch insert
            if origin_user_id not in users_in_batch:
                users_in_batch[origin_user_id] = user_name

            # Prepare post data (with placeholder for user_id)
            posts_data.append({
                "thread_id": thread_id,
                "origin_user_id": origin_user_id, # Store temporarily
                "content": content,
                "created_at": message_time,
                # "quote_ids": [], # Assuming empty for now
            })
            valid_lines_in_batch += 1
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Skipping invalid line in batch for thread {thread_id}: {e} - Line: {line[:100]}...")
            continue
            
    if not users_in_batch or not posts_data:
        print(f"  Skipping empty or invalid batch for thread {thread_id}")
        return 0

    try:
        # --- Batch Insert/Update Users --- 
        user_values = [
            {
                "user_name": name,
                "email": f"{uid}@gmail.com",
                "origin_user_id": uid,
                "hashed_password": get_password_hash("12345678"),
            } for uid, name in users_in_batch.items()
        ]
        user_insert_stmt = insert(User).values(user_values)
        user_insert_stmt = user_insert_stmt.on_conflict_do_nothing(index_elements=["origin_user_id"])
        db.execute(user_insert_stmt)
        # Don't commit yet

        # --- Get User ID Mapping --- 
        origin_to_db_id_map = get_user_id_map(db, set(users_in_batch.keys()))

        # --- Prepare Batch Post Insert Data --- 
        post_values_final = []
        processed_post_count = 0
        for post_draft in posts_data:
            origin_id = post_draft["origin_user_id"]
            db_user_id = origin_to_db_id_map.get(origin_id)
            if db_user_id:
                post_values_final.append({
                    "thread_id": post_draft["thread_id"],
                    "user_id": db_user_id,
                    "content": post_draft["content"],
                    "created_at": post_draft["created_at"],
                    # "quote_ids": post_draft["quote_ids"],
                })
                processed_post_count += 1
            else:
                print(f"  Skipping post in batch for thread {thread_id}: Could not find DB ID for origin user {origin_id}")
                
        if not post_values_final:
            print(f"  Skipping batch for thread {thread_id}: No valid posts after user ID mapping.")
            db.rollback() # Rollback the user insert if no posts are made
            return 0

        # --- Batch Insert Posts --- 
        post_insert_stmt = insert(Post).values(post_values_final)
        db.execute(post_insert_stmt)
        # Don't commit yet

        # --- Update Thread Count --- 
        thread_update_stmt = update(Thread).values(
            children_count=Thread.children_count + processed_post_count
        ).where(Thread.id == thread_id)
        db.execute(thread_update_stmt)

        # --- Commit Transaction --- 
        db.commit()
        return processed_post_count

    except Exception as e:
        print(f"ERROR processing batch for thread {thread_id}: {e}")
        db.rollback()
        return 0

if __name__ == "__main__":
    main()