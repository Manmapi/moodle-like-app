import os
import json
import pathlib
from pathlib import Path

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


# Example data:
# {"message_id": "22601839", "user_name": "Fire Of Heart", "message_time": "2023-01-04T02:38:06+0700", "content": "Ngồi suy nghĩ tổ chức cái gì cho đông người tham gia mà không quá khó cho mọi người, cuối cùng cũng nảy ra dc 1 ý tưởng như sau: \nChia sẻ kinh nghiệm phỏng vấn. \n \nThể lệ như sau: \n \n Bạn kể lại ngay trong thread này về những lần phỏng vấn của bạn trong năm 2021-2022. \n Bắt buộc: Phải ghi rõ tên công ty. \n Càng chi tiết càng tốt. Đầy đủ từng vòng từ khâu nộp cv qua đâu, coding online, home work v.v... \n Kể lại đầy đủ những câu hỏi phỏng vấn trong lần phỏng vấn đó. Cách bạn trả lời như nào. \n Đúc rút kinh nghiệm sau lần phỏng vấn đó. Vì sao thành công, vì sao tạch, chỗ nào trả lời tốt, chỗ nào trả lời dở.  Cái này là quan trọng nhất. Ko quan trọng là bạn nhận dc offer hay ko, quan trọng là rút ra dc những bài học nào để tiến bộ hơn. Khuyến khích mọi ng tham gia bất kể số năm kinh nghiệm, vị trí, v.v... \n \nGiải thưởng: \n \n Dành cho những post nào nhiều lượt ưng nhất, có nội dung tốt nhất. Cái này mình sẽ lựa theo cảm tính 1 phần nữa, nói trc vậy luôn cho khỏi thắc mắc. \n Sẽ có giải thưởng cho 3-5 người, bao gồm tít (Chắc chắn có) + hiện vật (xin sau, có thể có hoặc ko). \n \nFormat mẫu cho các bạn tham gia: \n \n \n Công ty: ABC \n Thời điểm phỏng vấn: 07/2022 \n Nơi nộp CV: HR contact qua linkedin \n Chuẩn bị: Đã dành 2 tuần để cày 100 bài code thiếu nhi, system design ở trang abcxyz... \n Round 1: \n Là 1 bài home work ko quá khó, độ khó cỡ leetcode medium, làm trong 60 phút. \nDo mình chưa nắm kỹ về cấu trúc dữ liệu Abcxyz nên dính TLE. Sau khi hết thời gian mới ngồi research và tìm ra cách giải tối ưu với kỹ thuật xyz. \n- Round 2: \nPhỏng vấn online qua google hangout với 1 anh abc xyz. \nĐầu tiên 2 bên giới thiệu lẫn nhau như bình thường, ấn tượng đầu tiên là anh ấy có vẻ hơi khó tính và nghiêm túc. Câu hỏi đầu tiên là 1 câu về OOP, yêu cầu mình giải thích tính chất XYZ. bla bla bla \n- Round X: \nGặp CTO abc xyz , bla bla bla \n- Round N: \nHR gửi offer nhưng mình thấy quá thấp nên đã thảo luận và deal lại lương. Mình đã nói là mức offer này chỉ cao hơn 10% so với offer hiện tại và đang có offer khác tốt hơn. Mình rất thích cty vì môi trường và tính ứng dụng của sản phẩm nhưng lương thấp vậy thì khó. Sau khi nghe chia sẻ HR đã gửi lại offer với mức cao hơn. \n- Kinh nghiệm sau lần phỏng vấn: Đã không trả lời tốt ở câu xyz vì lý do abc. Do ôn kỹ phần system design nên trả lời tự tin v.v.... \n \n \nCơ bản là thế, các bạn cứ linh động ko gò bó template nhé. \n \nThế nhé, hy vọng là sẽ đông người tham gia. Một người chia sẻ thì ko có gì nhiều nhưng nếu 10-100 người cùng tham gia sẽ có 1 tập kinh nghiệm phỏng vấn chất lượng. Giống thread chia sẻ lương vậy. \n \n Các thím muốn đóng góp gì về nội dung event thì tạm thời có thể đăng ở thread này luôn cũng dc. Sau này thống nhất rồi thì mình sẽ xóa sau cho đỡ loãng.", "quotes": [], "user_id": 873787}


def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Define data directory relative to script location (in the same folder)
    data_dir = script_dir / "data"
    
    print(f"Using data directory: {data_dir}")
    
    # read data from data_dir/<second_level_thread_name>/<third_level_thread_name>/data.json
    # Read line by line then parse to json
    # Insert into database
    for category_id, category_name in thread_mapping.items():
        # Get the base directory
        base_dir = data_dir / category_name
        
        # Check if directory exists
        if not base_dir.exists():
            print(f"Directory {base_dir} does not exist")
            continue
            
        # Loop for each folder in this path
        for third_level_dir in base_dir.iterdir():
            # Bypass if not a directory
            if not third_level_dir.is_dir():
                continue
                
            # Bypass folder starting with . like .DS_Store
            third_level_thread_name = third_level_dir.name
            if third_level_thread_name.startswith("."):
                continue
                
            # Use pathlib to handle path with special characters
            data_file = third_level_dir / "data.json"
            
            # Check if data file exists
            if not data_file.exists():
                print(f"Data file not found: {data_file}")
                continue
            with Session(engine) as db:
                # Read data from data.json
                try:
                    with open(data_file, "r", encoding="utf-8") as f:
                        # Get user from frist line => They will create the thread
                        first_line = f.readline()
                        data = json.loads(first_line)
                        user_id = data["user_id"]
                        user_name = data["user_name"]
                        # Try to insert the user
                        first_user_q = insert(User).values(
                            user_name=user_name,
                            email=f"{user_id}@gmail.com",
                            origin_user_id=user_id,
                            hashed_password=get_password_hash("12345678"),
                        ).on_conflict_do_nothing(index_elements=["origin_user_id"]).returning(User.id)

                        db_user_id = db.exec(first_user_q).scalar()
                        db.commit()

                        # If insert didn't work (user already exists), query for the existing user
                        if db_user_id is None:
                            # Get existing user ID
                            existing_user = db.exec(
                                select(User).where(User.origin_user_id == user_id)
                            ).first()
                            if existing_user:
                                db_user_id = existing_user.id
                        thread = Thread(
                            title=third_level_thread_name,
                            category_id=category_id,
                            user_id=db_user_id,
                            level=3,
                            children_count=0,
                        )
                        db.add(thread)
                        db.commit()
                        db.refresh(thread)

                        category_update_q = update(Category).values(children_count=Category.children_count + 1).where(Category.id == category_id)
                        db.exec(category_update_q)
                        db.commit()

                        thread_id = thread.id   
                        for line in f:
                            data = json.loads(line)
                            user_id = data["user_id"]
                            user_name = data["user_name"]
                            message_time = data["message_time"]
                            content = data["content"]
                            quotes = data["quotes"]
                            user_data = {  
                                "user_name": user_name,
                                "origin_user_id": user_id,
                                "email": f"{user_id}@gmail.com",
                                "hashed_password": get_password_hash("12345678"),
                            }
                            
                            post_data = {
                                "thread_id": thread.id,
                                "content": content,
                                "created_at": message_time,
                                "quote_ids": [],
                            }
                            
                            # Handle duplicate original_user_id in user_data
                            user_q = insert(User).values(user_data).on_conflict_do_nothing(index_elements=["origin_user_id"]).returning(User.id)
                            db_user_id = db.exec(user_q).scalar()
                            db.commit()
                            if db_user_id is None:
                                # Get existing user ID
                                existing_user = db.exec(
                                    select(User).where(User.origin_user_id == user_id)
                                ).first()
                                if existing_user:
                                    db_user_id = existing_user.id

                            post_data["user_id"] = db_user_id                
                            post_q = insert(Post).values(post_data)

                            thread_q = update(Thread).values(children_count=Thread.children_count + 1).where(Thread.id == thread_id)
                            db.exec(post_q)
                            db.exec(thread_q)
                            db.commit()
                        
                except Exception as e:
                    print(f"Error processing {data_file}: {e}")
            print("Handle file: ", data_file)

if __name__ == "__main__":
    main()  