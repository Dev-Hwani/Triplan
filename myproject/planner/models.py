from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password


# 1) 회원 (Signup)
class Signup(models.Model):
    email = models.EmailField(primary_key=True, verbose_name="이메일")
    password = models.CharField(max_length=100, verbose_name="비밀번호")
    name = models.CharField(max_length=50, verbose_name="이름")
    birth_date = models.DateField(null=True, blank=True, verbose_name="생년월일")
    address = models.CharField(max_length=200, blank=True, verbose_name="주소")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="전화번호")

    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # 비밀번호 평문 저장 방지 → 자동 암호화
        if not self.password.startswith("pbkdf2_"):  # 이미 암호화된 경우 제외
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    class Meta:
        db_table = "user"
        verbose_name = "회원"
        verbose_name_plural = "회원"


# 2) 여행 일정 (Planner)
class Planner(models.Model):
    id = models.AutoField(primary_key=True, db_column="planner_id")
    region = models.CharField(max_length=100, blank=True, verbose_name="지역", db_index=True)
    plan_image = models.ImageField(upload_to="planner_images/", null=True, blank=True, verbose_name="일정 이미지")
    start_date = models.DateField(null=True, blank=True, verbose_name="시작일")
    end_date = models.DateField(null=True, blank=True, verbose_name="종료일")

    def __str__(self):
        return f"Planner {self.id} - {self.region}"

    class Meta:
        db_table = "planner"
        verbose_name = "여행 일정"
        verbose_name_plural = "여행 일정"


# 3) 관광지 정보 (Tourlist)
class Tourlist(models.Model):
    id = models.AutoField(primary_key=True, db_column="tourlist_id")
    title = models.CharField(max_length=200, verbose_name="관광지명", db_index=True)
    address = models.CharField(max_length=200, blank=True, verbose_name="주소")
    area_code = models.IntegerField(null=True, blank=True, verbose_name="지역 코드", db_index=True)
    sigungu_code = models.IntegerField(null=True, blank=True, verbose_name="시군구 코드", db_index=True)
    image = models.ImageField(upload_to="tour_images/", null=True, blank=True, verbose_name="이미지")
    read_count = models.IntegerField(default=0, verbose_name="조회수")
    pin_count = models.IntegerField(default=0, verbose_name="찜 수")

    def __str__(self):
        return self.title

    class Meta:
        db_table = "tourlist"
        verbose_name = "관광지 정보"
        verbose_name_plural = "관광지 정보"


# 4) 일정 상세 (PlannerDetail)
class PlannerDetail(models.Model):
    id = models.AutoField(primary_key=True, db_column="planner_detail_id")
    plan_name = models.CharField(max_length=200, verbose_name="상세 일정명")
    planner = models.ForeignKey(Planner, on_delete=models.CASCADE)
    user = models.ForeignKey(Signup, on_delete=models.CASCADE)
    tourlist = models.ForeignKey(Tourlist, on_delete=models.CASCADE)
    written_date = models.DateTimeField(default=timezone.now, verbose_name="작성일")
    actual_date = models.DateField(null=True, blank=True, verbose_name="실제 날짜")
    memo = models.TextField(blank=True, verbose_name="메모")

    def __str__(self):
        return self.plan_name

    class Meta:
        db_table = "planner_detail"
        verbose_name = "일정 상세"
        verbose_name_plural = "일정 상세"


# 5) 피드 (Feed)
class Feed(models.Model):
    id = models.AutoField(primary_key=True, db_column="feed_id")
    author = models.ForeignKey(Signup, on_delete=models.CASCADE, verbose_name="작성자")
    image = models.ImageField(upload_to="feed_images/", null=True, blank=True, verbose_name="이미지")
    content = models.TextField(blank=True, verbose_name="내용")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="작성일", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    def __str__(self):
        return f"{self.author.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        db_table = "feed"
        verbose_name = "피드"
        verbose_name_plural = "피드"


# 6) 댓글 (Reply)
class Reply(models.Model):
    id = models.AutoField(primary_key=True, db_column="reply_id")
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(Signup, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="댓글 내용")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="작성일", db_index=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="child_replies")

    def __str__(self):
        return f"Reply {self.id} by {self.author.email}"

    class Meta:
        db_table = "reply"
        verbose_name = "댓글"
        verbose_name_plural = "댓글"


# 7) 좋아요 (Like)
class Like(models.Model):
    id = models.AutoField(primary_key=True, db_column="like_id")
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="likes")
    author = models.ForeignKey(Signup, on_delete=models.CASCADE)
    is_like = models.BooleanField(default=True)

    def __str__(self):
        return f"Like on {self.feed.id} by {self.author.email}"

    class Meta:
        db_table = "like"
        verbose_name = "좋아요"
        verbose_name_plural = "좋아요"
        constraints = [
            models.UniqueConstraint(fields=["feed", "author"], name="unique_like")
        ]


# 8) 북마크 (Bookmark)
class Bookmark(models.Model):
    id = models.AutoField(primary_key=True, db_column="bookmark_id")
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="bookmarks")
    author = models.ForeignKey(Signup, on_delete=models.CASCADE)
    is_marked = models.BooleanField(default=True)

    def __str__(self):
        return f"Bookmark on {self.feed.id} by {self.author.email}"

    class Meta:
        db_table = "bookmark"
        verbose_name = "북마크"
        verbose_name_plural = "북마크"
        constraints = [
            models.UniqueConstraint(fields=["feed", "author"], name="unique_bookmark")
        ]
