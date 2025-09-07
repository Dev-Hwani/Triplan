import json, os, re, random, string, logging, openai, requests
from uuid import uuid4
from datetime import datetime, timedelta  # 추가: 날짜 계산을 위해
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse, HttpResponseNotAllowed
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.core.paginator import Paginator
from .models import Signup, Planner, Tourlist, PlannerDetail, Feed, Reply, Like, Bookmark
from django.contrib.auth import get_user_model
from django.core.mail import send_mail  # 실제 메일 전송 시 사용 (설정 필요)
from django.contrib.auth.hashers import make_password, check_password  # 해시 처리를 위한 함수
from django.contrib import messages
User = get_user_model()

def main_page(request):
    regions = [
        {"name": "서울", "img": "seoul.jpg"},
        {"name": "부산", "img": "busan.jpg"},
        {"name": "제주도", "img": "jeju.jpg"},
        {"name": "강릉", "img": "gangneung.jpg"},
        {"name": "경주", "img": "gyeongju.jpg"},
        {"name": "영월", "img": "yeongwol.jpg"},
        {"name": "전주", "img": "jeonju.jpg"},
        {"name": "여수", "img": "yeosu.jpg"},
        {"name": "인천", "img": "incheon.jpg"},
        {"name": "속초", "img": "sokcho.jpg"},
        {"name": "대구", "img": "daegu.jpg"},
        {"name": "춘천", "img": "chuncheon.jpg"}
    ]
    context = {
        "regions": regions,
    }
    return render(request, "planner/main_page.html", context)


@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        name = request.POST.get('name')
        birth_date = request.POST.get('birth_date')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')

        # 서버 측 검증

        # 이메일 검증
        var_email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(var_email_pattern, email):
            return JsonResponse({'status': 'error', 'message': '유효하지 않은 이메일 형식입니다.'}, status=400)

        # 비밀번호 검증: 8~16자, 영문 대소문자, 숫자, 특수문자 포함
        var_password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>\/?]).{8,16}$'
        if not re.match(var_password_pattern, password):
            return JsonResponse({'status': 'error', 'message': '비밀번호는 8~16자 영문 대소문자, 숫자, 특수문자를 포함해야 합니다.'}, status=400)

        if password != password_confirm:
            return JsonResponse({'status': 'error', 'message': '비밀번호와 비밀번호 재확인이 일치하지 않습니다.'}, status=400)

        # 중복 가입 검사
        try:
            existing_user = Signup.objects.get(email=email)
            if existing_user.is_active:
                return JsonResponse({'status': 'error', 'message': '이미 가입된 이메일입니다.'}, status=400)
            else:
                # 탈퇴된 계정이면 업데이트하여 재가입 처리
                existing_user.password = make_password(password)
                existing_user.name = name
                existing_user.birth_date = birth_date if birth_date else None
                existing_user.address = address
                existing_user.phone_number = phone_number
                existing_user.is_active = True
                existing_user.save()
                return JsonResponse({'status': 'success', 'message': '회원가입 성공'})
        except Signup.DoesNotExist:
            # 존재하지 않는 경우에는 새로 생성
            Signup.objects.create(
                email=email,
                password=make_password(password),
                name=name,
                birth_date=birth_date if birth_date else None,
                address=address,
                phone_number=phone_number,
                is_active=True
            )
            return JsonResponse({'status': 'success', 'message': '회원가입 성공'})
    else:
        return render(request, 'planner/signup.html')



@csrf_exempt
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            user = Signup.objects.get(email=email)
            # 활성화 상태가 아니면 로그인 실패 처리
            if not user.is_active:
                return JsonResponse({"status": "error", "message": "아이디 또는 비밀번호가 올바르지 않습니다."}, status=403)
            if check_password(password, user.password):
                request.session["user_email"] = user.email
                request.session["user_name"] = user.name
                return JsonResponse({"status": "success", "user_name": user.name})
            else:
                raise Signup.DoesNotExist
        except Signup.DoesNotExist:
            return JsonResponse({"status": "error", "message": "아이디 또는 비밀번호가 올바르지 않습니다."}, status=400)
    else:
        return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)


def logout_view(request):
    request.session.flush()  # 세션 데이터 초기화
    return redirect('main_page')


@csrf_exempt
def password_reset_view(request):
    """
    비밀번호 찾기:
    사용자가 본인의 이메일과 이름을 입력하면, 해당 회원 정보를 확인하고,
    임시 비밀번호(8자리)를 생성하여 회원의 비밀번호를 해시 처리한 후 업데이트하고,
    전용 발신자 계정을 사용하여 임시 비밀번호를 이메일로 전송합니다.
    """
    if request.method == "POST":
        email = request.POST.get("email")
        name = request.POST.get("name")
        try:
            user = Signup.objects.get(email=email, name=name)
        except Signup.DoesNotExist:
            return JsonResponse({"status": "error", "message": "해당 회원 정보를 찾을 수 없습니다."}, status=400)

        # 임시 비밀번호 생성 (8자리)
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # 비밀번호 해시 처리 후 업데이트
        user.password = make_password(temp_password)
        user.save()

        # 이메일 전송 (전용 발신자 계정을 사용하여 settings.py의 EMAIL 설정에 따라 처리됨)
        subject = "여행 플래너 임시 비밀번호 안내"
        message = (
            f"안녕하세요, {user.name}님.\n\n"
            f"요청하신 임시 비밀번호는 {temp_password} 입니다.\n"
            "로그인 후 반드시 비밀번호를 변경해 주세요.\n\n"
            "감사합니다."
        )
        recipient_list = [user.email]

        try:
            send_mail(subject, message, None, recipient_list, fail_silently=False)
            # 발신자 정보를 생략하면 settings.py의 DEFAULT_FROM_EMAIL이 사용됩니다.
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"이메일 전송에 실패했습니다: {e}"}, status=500)

        return JsonResponse({"status": "success", "message": "임시 비밀번호가 이메일로 전송되었습니다. 이메일을 확인해 주세요."})
    else:
        return render(request, 'planner/password_reset.html')


def search_view(request):
    """
    검색 페이지:
    사용자가 여행지명을 입력하여 검색할 수 있도록 하는 페이지입니다.
    폼 제출 시 GET 방식으로 plan_schedule 뷰에 destination 파라미터를 전달합니다.
    """
    return render(request, 'planner/search.html')


def my_page_view(request):
    """
    마이페이지: 로그인한 사용자의 회원정보와 '나의 일정'을 함께 표시합니다.
    """
    user_email = request.session.get('user_email')
    if not user_email:
        return redirect('login')
    try:
        user = Signup.objects.get(email=user_email)
    except Signup.DoesNotExist:
        return redirect('login')

    # PlannerDetail을 통해 연결된 Planner들을 가져옵니다.
    planners = Planner.objects.all().distinct()
    current_date = timezone.now().date()

    # end_date를 기준으로 다가올 여행 일정과 지난 여행 일정을 구분
    upcoming_plans = planners.filter(end_date__gte=current_date).order_by("start_date")
    past_plans = planners.filter(end_date__lt=current_date).order_by("-start_date")

    # 각 Planner에 대해 여행 제목은 PlannerDetail의 plan_name에서 추출
    def get_travel_title(plan):
        detail = plan.plannerdetail_set.order_by("written_date").first()
        if detail:
            return detail.plan_name
        return plan.region  # 없으면 지역명을 대체값으로 사용

    upcoming_list = []
    for plan in upcoming_plans:
        upcoming_list.append({
            "plan_no": plan.id,
            "travel_title": get_travel_title(plan),
            "plan_img": plan.plan_image,
            "sdate": plan.start_date,
            "edate": plan.end_date,
            "region": plan.region,
        })

    past_list = []
    for plan in past_plans:
        past_list.append({
            "plan_no": plan.id,
            "travel_title": get_travel_title(plan),
            "plan_img": plan.plan_image,
            "sdate": plan.start_date,
            "edate": plan.end_date,
            "region": plan.region,
        })

    context = {
        "user": user,
        "upcoming_plans": upcoming_list,
        "past_plans": past_list,
    }
    return render(request, "planner/my_page.html", context)


def my_schedule_view(request):
    # 로그인 체크: 로그인하지 않은 경우 로그인 페이지로 리다이렉트
    user_email = request.session.get("user_email")
    if not user_email:
        return redirect("login")
    try:
        user = Signup.objects.get(email=user_email)
    except Signup.DoesNotExist:
        return redirect("login")

    # PlannerDetail에서 연결된 Planner들을 가져옵니다.
    planners = Planner.objects.filter(plannerdetail__user=user).distinct()

    # 현재 날짜
    current_date = timezone.now().date()

    # end_date 기준으로 다가올 여행과 과거 여행 구분
    upcoming_plans = planners.filter(end_date__gte=current_date).order_by("start_date")
    past_plans = planners.filter(end_date__lt=current_date).order_by("-start_date")

    # 각 Planner에 대해 여행 제목 추출
    def get_travel_title(plan):
        detail = plan.plannerdetail_set.order_by("written_date").first()
        if detail:
            return detail.plan_name
        return plan.region  # 없으면 지역명을 대체값으로 사용

    # 여행 목록 준비
    upcoming_list = []
    for plan in upcoming_plans:
        upcoming_list.append({
            "plan_no": plan.id,
            "travel_title": get_travel_title(plan),
            "plan_img": plan.plan_image,  # 이미지 경로
            "sdate": plan.start_date,
            "edate": plan.end_date,
            "region": plan.region,
        })

    past_list = []
    for plan in past_plans:
        past_list.append({
            "plan_no": plan.id,
            "travel_title": get_travel_title(plan),
            "plan_img": plan.plan_image,
            "sdate": plan.start_date,
            "edate": plan.end_date,
            "region": plan.region,
        })

    context = {
        "upcoming_plans": upcoming_list,
        "past_plans": past_list,
    }
    return render(request, "planner/my_schedule.html", context)


@csrf_protect
def schedule_detail_view(request, plan_no):
    """
    특정 일정(Planner)의 상세 내용을 보여주는 페이지입니다.

    PlannerDetail 테이블의 모든 항목을 해당 Planner에 대해 조회하고,
    written_date(작성일) 또는 actual_date(실제 날짜)를 기준으로 그룹화하여 각 날짜별 일정 목록을 템플릿에 전달합니다.

    템플릿에서는 Planner(여행 일정) 정보와 함께, 각 날짜별(예: DAY 1, DAY 2, …) 일정 항목(관광지명, 메모 등)을 리스트 형태로 표시합니다.
    """
    # plan_no로 Planner 객체를 가져옵니다. (없으면 404)
    planner = get_object_or_404(Planner, id=plan_no)

    # 해당 Planner에 연결된 PlannerDetail 항목들을 actual_date 기준 오름차순으로 조회합니다.
    details = PlannerDetail.objects.filter(planner=planner).order_by('actual_date')

    # actual_date(실제 날짜)를 기준으로 PlannerDetail 항목들을 그룹화합니다.
    itinerary_by_day = {}
    for detail in details:
        day = detail.actual_date if detail.actual_date else detail.written_date.date()
        itinerary_by_day.setdefault(day, []).append(detail)

    # 그룹화된 날짜들을 정렬합니다.
    sorted_days = sorted(itinerary_by_day.keys())

    context = {
        "planner": planner,
        "itinerary_by_day": itinerary_by_day,
        "sorted_days": sorted_days,
    }
    return render(request, "planner/schedule_detail.html", context)


@csrf_exempt
def update_profile_view(request):
    """
    회원정보 수정: 로그인한 사용자의 정보를 업데이트합니다.
    선택적으로 새 비밀번호와 새 비밀번호 재확인을 입력하여 비밀번호를 변경할 수 있습니다.
    """
    user_email = request.session.get('user_email')
    if not user_email:
        return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
    try:
        user = Signup.objects.get(email=user_email)
    except Signup.DoesNotExist:
        return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)

    if request.method == 'POST':
        user.name = request.POST.get('name', user.name)
        user.address = request.POST.get('address', user.address)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        birth_date = request.POST.get('birth_date')
        if birth_date:
            user.birth_date = birth_date

        # 새 비밀번호 업데이트 (선택적)
        new_password = request.POST.get('new_password')
        new_password_confirm = request.POST.get('new_password_confirm')
        if new_password or new_password_confirm:
            if new_password != new_password_confirm:
                return JsonResponse({"status": "error", "message": "새 비밀번호와 재확인이 일치하지 않습니다."}, status=400)
            # 비밀번호 형식 검증: 8~16자, 영문 대소문자, 숫자, 특수문자 포함
            var_password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>\/?]).{8,16}$'
            if not re.match(var_password_pattern, new_password):
                return JsonResponse({"status": "error",
                                     "message": "새 비밀번호는 8~16자 영문 대소문자, 숫자, 특수문자를 포함해야 합니다."},
                                    status=400)
            user.password = make_password(new_password)

        user.save()
        return JsonResponse({"status": "success", "message": "회원정보가 업데이트 되었습니다."})
    else:
        return render(request, 'planner/update_profile.html', {'user': user})


@csrf_exempt
def delete_profile_view(request):
    """
    회원탈퇴: 로그인한 사용자가 자신의 회원정보를 탈퇴 처리합니다.
    실제로 데이터를 삭제하는 대신, is_active 값을 False로 설정합니다.
    """
    user_email = request.session.get('user_email')
    if not user_email:
        return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
    try:
        user = Signup.objects.get(email=user_email)
    except Signup.DoesNotExist:
        return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)
    if request.method == 'POST':
        # 탈퇴 시 is_active를 False로 변경
        user.is_active = False
        user.save()
        # 세션 초기화
        request.session.flush()
        return JsonResponse({"status": "success", "message": "회원탈퇴가 완료되었습니다."})
    else:
        return render(request, 'planner/delete_profile.html', {'user': user})

# Google Maps API
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
# 한국관광공사 API
KTO_API_KEY = os.getenv("KTO_API_KEY")

@csrf_protect
def plan_schedule_view(request):
    """
    일정 만들기/수정 페이지:
      - GET 요청 시:
          * edit_plan 파라미터가 있으면 해당 Planner와 관련 PlannerDetail 데이터를 불러와서
            폼에 미리 채울 데이터를 context에 담아 템플릿으로 전달합니다.
          * 없으면 일반 일정 작성 로직을 수행합니다.
      - POST 요청 시:
          * payload에 edit_plan 값이 있으면 기존 Planner를 업데이트(기존 PlannerDetail 삭제 후 새로 생성)하고,
            그렇지 않으면 새 일정을 생성합니다.
      참고: wdate는 CharField이므로 "YYYY-MM-DD" 형식의 문자열로 저장합니다.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "잘못된 JSON 데이터입니다."}, status=400)

        travel_title = data.get("travel_title")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        destination = data.get("destination")
        itineraries = data.get("itineraries", {})  # 예: {"1": [ {...}, {...} ], "2": [ ... ], ...}
        edit_plan = data.get("edit_plan")  # 수정 모드일 경우 Planner의 plan_no

        if not all([travel_title, start_date, end_date, destination]):
            return JsonResponse({"status": "error", "message": "필수 필드가 누락되었습니다."}, status=400)

        user_email = request.session.get("user_email")
        if not user_email:
            return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
        try:
            user = Signup.objects.get(email=user_email)
        except Signup.DoesNotExist:
            return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)

        if edit_plan:
            # 수정 모드: 기존 Planner 업데이트
            planner = get_object_or_404(Planner, plan_no=edit_plan)
            planner.region = destination
            planner.sdate = start_date
            planner.edate = end_date
            planner.save()
            # 기존 세부 일정 삭제
            PlannerDetail.objects.filter(planner=planner).delete()
        else:
            # 신규 일정 생성
            planner = Planner.objects.create(
                region=destination,
                plan_img="",
                sdate=start_date,
                edate=end_date
            )

        # 시작일을 datetime 객체로 변환 (형식: YYYY-MM-DD)
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            return JsonResponse({"status": "error", "message": "시작일 형식이 올바르지 않습니다."}, status=400)

        # 각 DAY의 itinerary 항목에 대해 PlannerDetail 레코드 생성
        for day, items in itineraries.items():
            try:
                day_int = int(day)
            except ValueError:
                continue
            calculated_date = start_date_obj + timedelta(days=day_int - 1)
            wdate_str = calculated_date.strftime("%Y-%m-%d")

            for index, item in enumerate(items, start=1):
                tour_title = item.get("name")
                if not tour_title:
                    continue
                try:
                    tour = Tourlist.objects.get(title=tour_title)
                except Tourlist.DoesNotExist:
                    tour = Tourlist.objects.create(
                        title=tour_title,
                        addr1=item.get("address", ""),
                        areacode=None,
                        sigungucode=None,
                        image2="",
                        readcount=0,
                        ping=0,
                    )
                memo_value = item.get("memo", "")
                PlannerDetail.objects.create(
                    plan_name=travel_title,
                    planner=planner,
                    signup=user,
                    title=tour,
                    wdate=f"DAY {day}",
                    actual_date=wdate_str,
                    memo=memo_value
                )
        return JsonResponse({"status": "success", "message": "일정이 저장되었습니다."})
    else:
        # GET 요청 처리
        edit_plan = request.GET.get("edit_plan")
        if edit_plan:
            planner = get_object_or_404(Planner, plan_no=edit_plan)
            details = PlannerDetail.objects.filter(planner=planner).order_by('wdate')
            travel_title = details.first().plan_name if details.exists() else planner.region
            itineraries = {}
            if planner.sdate:
                start_date_obj = planner.sdate  # 이미 date 타입입니다.
                for detail in details:
                    if detail.actual_date:  # actual_date 필드 사용
                        day_num = (detail.actual_date - start_date_obj).days + 1
                        itineraries.setdefault(day_num, []).append({
                            "name": detail.title.title,
                            "address": detail.title.addr1,
                            "memo": detail.memo,
                        })
            # 추천 장소 로직 (수정 모드에서는 기존 Planner.region 사용)
            dest = planner.region
            recommended_places = []
            search_lat, search_lng = None, None
            if dest:
                google_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={dest}&language=ko&key={GOOGLE_MAPS_API_KEY}"
                google_response = requests.get(google_url)
                google_places = google_response.json()
                if "results" in google_places and google_places["results"]:
                    first_place = google_places["results"][0]
                    search_lat = first_place["geometry"]["location"]["lat"]
                    search_lng = first_place["geometry"]["location"]["lng"]
                    for place in google_places["results"]:
                        recommended_places.append({
                            "name": place["name"],
                            "address": place.get("formatted_address", ""),
                            "description": place.get("types", []),
                            "lat": place["geometry"]["location"]["lat"],
                            "lng": place["geometry"]["location"]["lng"],
                        })
                if search_lat and search_lng:
                    nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={search_lat},{search_lng}&radius=2000&language=ko&key={GOOGLE_MAPS_API_KEY}"
                    nearby_response = requests.get(nearby_url)
                    nearby_places = nearby_response.json()
                    for place in nearby_places.get("results", []):
                        recommended_places.append({
                            "name": place["name"],
                            "address": place.get("vicinity", ""),
                            "description": place.get("types", []),
                            "lat": place["geometry"]["location"]["lat"],
                            "lng": place["geometry"]["location"]["lng"],
                        })
                api_url = "http://apis.data.go.kr/B551011/KorService1/searchKeyword1"
                params = {
                    "serviceKey": KTO_API_KEY,
                    "keyword": dest,
                    "numOfRows": 100,
                    "pageNo": 1,
                    "MobileOS": "ETC",
                    "MobileApp": "AppTest",
                    "_type": "json"
                }
                try:
                    ktour_response = requests.get(api_url, params=params)
                    ktour_response.raise_for_status()  # HTTP 오류 시 예외 발생
                    ktour_places = ktour_response.json()
                    # 디버깅: 서버 콘솔에 API 응답 출력
                    print("KTO API 응답:", json.dumps(ktour_places, indent=2, ensure_ascii=False))
                    items = ktour_places.get("response", {}).get("body", {}).get("items", {}).get("item", [])

                    # items가 딕셔너리인 경우 리스트로 변환
                    if isinstance(items, dict):
                        items = [items]

                    for place in items:
                        ct = place.get("contenttypeid", "")
                        if ct not in ["12", "14"]:
                            continue  # contentTypeId가 12나 14가 아니면 건너뜁니다.
                        firstimage2 = place.get("firstimage2")
                        if not firstimage2:
                            continue
                        recommended_places.append({
                            "name": place.get("title", ""),
                            "address": place.get("addr1", ""),
                            "description": place.get("contenttypeid", "설명 없음"),
                            "firstimage2": place.get("firstimage2", "https://via.placeholder.com/200?text=No+Image"),
                            "description": ct,
                            "lat": place.get("mapy", ""),
                            "lng": place.get("mapx", ""),
                            "source": "kto"
                        })
                except requests.exceptions.RequestException as e:
                    print(f"한국관광공사 API 요청 중 오류 발생: {e}")
            if search_lat is None or search_lng is None:
                map_center = {"lat": 36.5, "lng": 127.5}
            else:
                map_center = {"lat": search_lat, "lng": search_lng}
            context = {
                "edit_plan": edit_plan,  # 수정 모드에서는 Planner의 plan_no를 전달
                "travel_title": travel_title,
                "start_date": planner.sdate,
                "end_date": planner.edate,
                "destination": planner.region,
                "itineraries": json.dumps(itineraries),
                "recommended_places": recommended_places,
                "recommended_json": json.dumps(recommended_places),
                "google_map_api_key": GOOGLE_MAPS_API_KEY,
                "map_center": map_center,
            }
            return render(request, "planner/plan_schedule.html", context)
        else:
            destination = request.GET.get("destination", "")
            recommended_places = []
            search_lat, search_lng = None, None

            if destination:
                # 1. Google Places API - Text Search
                google_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={destination}&language=ko&key={GOOGLE_MAPS_API_KEY}"
                google_response = requests.get(google_url)
                google_places = google_response.json()
                if "results" in google_places and google_places["results"]:
                    first_place = google_places["results"][0]
                    search_lat = first_place["geometry"]["location"]["lat"]
                    search_lng = first_place["geometry"]["location"]["lng"]
                    for place in google_places["results"]:
                        recommended_places.append({
                            "name": place["name"],
                            "address": place.get("formatted_address", ""),
                            "description": place.get("types", []),
                            "lat": place["geometry"]["location"]["lat"],
                            "lng": place["geometry"]["location"]["lng"],
                        })
                # 2. Google Places API - Nearby Search
                # if search_lat and search_lng:
                #     nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={search_lat},{search_lng}&radius=2000&language=ko&key={GOOGLE_MAPS_API_KEY}"
                #     nearby_response = requests.get(nearby_url)
                #     nearby_places = nearby_response.json()
                #     for place in nearby_places.get("results", []):
                #         recommended_places.append({
                #             "name": place["name"],
                #             "address": place.get("vicinity", ""),
                #             "description": place.get("types", []),
                #             "lat": place["geometry"]["location"]["lat"],
                #             "lng": place["geometry"]["location"]["lng"],
                #         })
                # 3. 한국관광공사 API
                api_url = "http://apis.data.go.kr/B551011/KorService1/searchKeyword1"
                params = {
                    "serviceKey": KTO_API_KEY,
                    "keyword": destination,
                    "numOfRows": 100,
                    "pageNo": 1,
                    "MobileOS": "ETC",
                    "MobileApp": "AppTest",
                    "_type": "json"
                }
                try:
                    ktour_response = requests.get(api_url, params=params)
                    ktour_response.raise_for_status()  # HTTP 오류 시 예외 발생
                    ktour_places = ktour_response.json()
                    # 디버깅: 서버 콘솔에 API 응답 출력
                    print("KTO API 응답:", json.dumps(ktour_places, indent=2, ensure_ascii=False))
                    items = ktour_places.get("response", {}).get("body", {}).get("items", {}).get("item", [])

                    # items가 딕셔너리인 경우 리스트로 변환
                    if isinstance(items, dict):
                        items = [items]

                    for place in items:
                        ct = place.get("contenttypeid", "")
                        if ct not in ["12", "14"]:
                            continue  # contentTypeId가 12나 14가 아니면 건너뜁니다.
                        firstimage2 = place.get("firstimage2")
                        if not firstimage2:
                            continue
                        recommended_places.append({
                            "name": place.get("title", ""),
                            "address": place.get("addr1", ""),
                            "description": place.get("contenttypeid", "설명 없음"),
                            "firstimage2": place.get("firstimage2", "https://via.placeholder.com/200?text=No+Image"),
                            "description": ct,
                            "lat": place.get("mapy", ""),
                            "lng": place.get("mapx", ""),
                            "source": "kto"
                        })
                except requests.exceptions.RequestException as e:
                    print(f"한국관광공사 API 요청 중 오류 발생: {e}")

            if search_lat is None or search_lng is None:
                map_center = {"lat": 36.5, "lng": 127.5}
            else:
                map_center = {"lat": search_lat, "lng": search_lng}
            context = {
                "destination": destination,
                "recommended_places": recommended_places,
                "recommended_json": json.dumps(recommended_places),
                "google_map_api_key": GOOGLE_MAPS_API_KEY,
                "map_center": map_center,
            }
            return render(request, 'planner/plan_schedule.html', context)

# OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")
logger = logging.getLogger(__name__)

@csrf_exempt
def chatbot(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "")

        system_prompt = (
            "너는 전문 여행 컨설턴트야. "
            "사용자에게 맞춤형 여행 계획을 제안하고, 여행지 정보와 일정 조정에 대해 상세하게 답변해줘. "
            "모든 답변은 구체적이고, 실용적인 정보를 제공하며, 한 문장이 끝날 때마다 HTML <br> 태그를 사용하여 일정 구분을 표시해줘."
        )

        # 최신 OpenAI API 호출 (올바른 방식)
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user","content": user_message},
            ]
        )

        bot_reply = response['choices'][0]['message']['content'].strip()  # 결과 추출
        return JsonResponse({"reply": bot_reply})

    except json.JSONDecodeError:
        logger.error("JSON Decode Error: 요청 데이터가 올바르지 않습니다.")
        return JsonResponse({"reply": "잘못된 JSON 데이터입니다."}, status=400)

    except Exception as e:
        logger.error(f"Chatbot Error: {e}")  # 서버 로그에 오류 기록
        return JsonResponse({"reply": f"서버 오류 발생: {str(e)}"}, status=500)

@csrf_exempt
def save_schedule_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "잘못된 JSON 데이터입니다."}, status=400)

        travel_title = data.get("travel_title")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        destination = data.get("destination")
        itineraries = data.get("itineraries", {})  # {"1": [ {...}, {...} ], "2": [ ... ], ...}

        if not all([travel_title, start_date, end_date, destination]):
            return JsonResponse({"status": "error", "message": "필수 필드가 누락되었습니다."}, status=400)

        user_email = request.session.get("user_email")
        if not user_email:
            return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
        try:
            user = Signup.objects.get(email=user_email)
        except Signup.DoesNotExist:
            return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)

        edit_plan = data.get("edit_plan")
        if edit_plan:
            # 수정 모드: 기존 Planner 업데이트
            planner = get_object_or_404(Planner, plan_no=edit_plan)
            planner.region = destination
            planner.start_date = start_date
            planner.end_date = end_date
            planner.save()
            PlannerDetail.objects.filter(planner=planner).delete()
        else:
            # 신규 일정 생성
            planner = Planner.objects.create(
                region=destination,
                plan_image="",
                start_date=start_date,
                end_date=end_date
            )

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"status": "error", "message": "시작일 형식이 올바르지 않습니다."}, status=400)

        # DAY별 itinerary 처리
        for day, items in itineraries.items():
            try:
                day_int = int(day)
            except ValueError:
                continue
            calculated_date = start_date_obj + timedelta(days=day_int - 1)  # 실제 날짜
            for item in items:
                tour_title = item.get("name")
                if not tour_title:
                    continue
                tour, created = Tourlist.objects.get_or_create(
                    title=tour_title,
                    defaults={
                        "addr1": item.get("address", ""),
                        "areacode": None,
                        "sigungucode": None,
                        "image2": "",
                        "readcount": 0,
                        "ping": 0,
                    }
                )
                memo_value = item.get("memo", "")
                PlannerDetail.objects.create(
                    plan_name=travel_title,
                    planner=planner,
                    signup=user,
                    title=tour,
                    wdate=f"DAY {day}",       # 표시용
                    actual_date=calculated_date,  # DateField에 맞게 date 타입 저장
                    memo=memo_value
                )

        return JsonResponse({"status": "success", "message": "일정이 저장되었습니다."})
    else:
        return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)


@csrf_exempt
def update_destination_view(request):
    """
    AJAX GET 요청으로 전달된 destination을 기반으로,
    Google Places API (Text Search, Nearby Search)와 한국관광공사 API를 사용해
    추천 장소 데이터를 수집하고, 해당 지역의 지도 중심 좌표와 함께 JSON으로 반환합니다.
    """
    # GET 요청 처리: 기존 코드 그대로 추천 장소 수집 등
    destination = request.GET.get("destination", "")
    recommended_places = []
    search_lat, search_lng = None, None

    if destination:
        # 1. Google Places API - Text Search
        google_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={destination}&language=ko&key={GOOGLE_MAPS_API_KEY}"
        google_response = requests.get(google_url)
        google_places = google_response.json()
        if "results" in google_places and google_places["results"]:
            first_place = google_places["results"][0]
            search_lat = first_place["geometry"]["location"]["lat"]
            search_lng = first_place["geometry"]["location"]["lng"]
            for place in google_places["results"]:
                recommended_places.append({
                    "name": place["name"],
                    "address": place.get("formatted_address", ""),
                    "description": place.get("types", []),
                    "lat": place["geometry"]["location"]["lat"],
                    "lng": place["geometry"]["location"]["lng"],
                })
        # 2. Google Places API - Nearby Search
        # if search_lat and search_lng:
        #     nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={search_lat},{search_lng}&radius=2000&language=ko&key={GOOGLE_MAPS_API_KEY}"
        #     nearby_response = requests.get(nearby_url)
        #     nearby_places = nearby_response.json()
        #     for place in nearby_places.get("results", []):
        #         recommended_places.append({
        #             "name": place["name"],
        #             "address": place.get("vicinity", ""),
        #             "description": place.get("types", []),
        #             "lat": place["geometry"]["location"]["lat"],
        #             "lng": place["geometry"]["location"]["lng"],
        #         })
        # 3. 한국관광공사 API
        api_url = "http://apis.data.go.kr/B551011/KorService1/searchKeyword1"
        params = {
            "serviceKey": KTO_API_KEY,
            "keyword": destination,
            "numOfRows": 100,
            "pageNo": 1,
            "MobileOS": "ETC",
            "MobileApp": "AppTest",
            "_type": "json"
        }
        try:
            ktour_response = requests.get(api_url, params=params)
            ktour_response.raise_for_status()  # HTTP 오류 시 예외 발생
            ktour_places = ktour_response.json()
            # 디버깅: 서버 콘솔에 API 응답 출력
            print("KTO API 응답:", json.dumps(ktour_places, indent=2, ensure_ascii=False))
            items = ktour_places.get("response", {}).get("body", {}).get("items", {}).get("item", [])

            # items가 딕셔너리인 경우 리스트로 변환
            if isinstance(items, dict):
                items = [items]

            for place in items:
                # 필터링: contentTypeId가 "12" 또는 "14"인 경우만 처리
                ct = place.get("contenttypeid", "")
                if ct not in ["12", "14"]:
                    continue
                firstimage2 = place.get("firstimage2")
                if not firstimage2:
                    continue

                recommended_places.append({
                    "name": place.get("title", ""),
                    "address": place.get("addr1", ""),
                    "description": ct,
                    "firstimage2": place.get("firstimage2", "https://via.placeholder.com/200?text=No+Image"),
                    "lat": place.get("mapy", ""),
                    "lng": place.get("mapx", ""),
                    "source": "kto"
                })
        except requests.exceptions.RequestException as e:
            print(f"한국관광공사 API 요청 중 오류 발생: {e}")

    if search_lat is None or search_lng is None:
        map_center = {"lat": 36.5, "lng": 127.5}
    else:
        map_center = {"lat": search_lat, "lng": search_lng}
    context = {
        "destination": destination,
        "recommended_places": recommended_places,
        "recommended_json": json.dumps(recommended_places),
        "google_map_api_key": GOOGLE_MAPS_API_KEY,
        "map_center": map_center,
    }
    return JsonResponse({
        "destination": destination,
        "map_center": map_center,
        "recommended_places": recommended_places
    })

@csrf_exempt
def schedule_delete_view(request, plan_no):
    user_email = request.session.get("user_email")
    if not user_email:
        return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
    try:
        planner = Planner.objects.get(plan_no=plan_no)
        if not PlannerDetail.objects.filter(planner=planner, signup__email=user_email).exists():
            return JsonResponse({"status": "error", "message": "삭제 권한이 없습니다."}, status=403)
        planner.delete()
        return JsonResponse({"status": "success", "message": "일정이 삭제되었습니다."})
    except Planner.DoesNotExist:
        return JsonResponse({"status": "error", "message": "일정을 찾을 수 없습니다."}, status=404)


# 메인 피드 페이지: 로그인한 사용자의 피드를 인스타그램 피드처럼 보여줌
def feed_main(request):
    user_email = request.session.get('user_email')
    if not user_email:
        return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)

    try:
        user = Signup.objects.get(email=user_email)
    except Signup.DoesNotExist:
        return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)

    feed_object_list = Feed.objects.all().order_by('-id')
    feed_list = []

    for feed in feed_object_list:
        user_feed = feed.author  # Signup 인스턴스
        reply_object_list = Reply.objects.filter(feed=feed)
        reply_list = []

        for reply in reply_object_list:
            reply_author = reply.author
            reply_list.append({
                "reply_content": reply.reply_content,
                "nickname": reply_author.name if reply_author else "",
            })

        like_count = Like.objects.filter(feed=feed, is_like=True).count()
        is_liked = Like.objects.filter(feed=feed, author=user, is_like=True).exists()
        is_marked = Bookmark.objects.filter(feed=feed, author=user, is_marked=True).exists()

        feed_list.append({
            "id": feed.id,
            "image": feed.image.url if feed.image else "",
            "content": feed.content,
            "like_count": like_count,
            "profile_image": "",  # 기본 프로필 이미지 처리 가능
            "nickname": user_feed.name if user_feed else "",
            "reply_list": reply_list,
            "is_liked": is_liked,
            "is_marked": is_marked,
        })

    context = {
        "feeds": feed_list,
        "user": user_email,
    }

    return render(request, "planner/feed_main.html", context)


# 피드 업로드: POST 요청 시 이미지 파일과 글 내용을 저장
def upload_feed(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"status": "error", "message": "파일이 없습니다."}, status=400)

    content_text = request.POST.get('content', '')
    email = request.session.get('user_email')
    if not email:
        return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)

    user = get_object_or_404(Signup, email=email)

    # 파일 저장
    uuid_name = uuid4().hex
    save_dir = os.path.join(settings.MEDIA_ROOT, 'feed_images')
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, uuid_name)

    with open(save_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    # Feed 생성
    Feed.objects.create(
        author=user,
        image='feed_images/' + uuid_name,
        content=content_text
    )

    return JsonResponse({"status": "success"}, status=200)

# 댓글 업로드: POST 요청 시 댓글 저장
def upload_reply(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)

    feed_id = request.POST.get("feed_id")
    reply_content = request.POST.get("reply_content")
    email = request.session.get("user_email")

    if not feed_id or not reply_content or not email:
        return JsonResponse({"status": "error", "message": "필요한 데이터가 누락되었습니다."}, status=400)

    # 로그인 사용자 가져오기
    user = get_object_or_404(Signup, email=email)

    # 피드 가져오기
    feed = get_object_or_404(Feed, id=feed_id)

    # Reply 생성
    Reply.objects.create(
        feed=feed,
        reply_content=reply_content,
        author=user
    )

    return JsonResponse({"status": "success"}, status=200)

# 좋아요 토글 기능
def toggle_like(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "JSON 데이터 오류"}, status=400)
        feed_id = data.get("feed_id")
        favorite_text = data.get("favorite_text", "favorite_border")
        is_like = True if favorite_text == "favorite_border" else False
        email = request.session.get("user_email")
        if not email:
            return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
        user = Signup.objects.filter(email=email).first()
        if not user:
            return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)
        like = Like.objects.filter(feed_id=feed_id, author=user).first()
        if like:
            like.is_like = is_like
            like.save()
        else:
            Like.objects.create(feed_id=feed_id, is_like=is_like, author=user)
        return JsonResponse({"status": "success"}, status=200)
    return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)

# 북마크 토글 기능
def toggle_bookmark(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "JSON 데이터 오류"}, status=400)
        feed_id = data.get("feed_id")
        bookmark_text = data.get("bookmark_text", "bookmark_border")
        is_marked = True if bookmark_text == "bookmark_border" else False
        email = request.session.get("user_email")
        if not email:
            return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
        user = Signup.objects.filter(email=email).first()
        if not user:
            return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)
        bookmark = Bookmark.objects.filter(feed_id=feed_id, author=user).first()
        if bookmark:
            bookmark.is_marked = is_marked
            bookmark.save()
        else:
            Bookmark.objects.create(feed_id=feed_id, is_marked=is_marked, author=user)
        return JsonResponse({"status": "success"}, status=200)
    return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)

@csrf_exempt
def comment_reply(request, parent_id):
    if request.method == "POST":
        user_email = request.session.get("user_email")
        if not user_email:
            return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
        try:
            user = Signup.objects.get(email=user_email)
        except Signup.DoesNotExist:
            return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)
        try:
            parent_comment = Reply.objects.get(id=parent_id)
        except Reply.DoesNotExist:
            return JsonResponse({"status": "error", "message": "부모 댓글을 찾을 수 없습니다."}, status=404)
        reply_content = request.POST.get("reply_content", "").strip()
        if not reply_content:
            return JsonResponse({"status": "error", "message": "답글 내용을 입력해 주세요."}, status=400)
        new_reply = Reply.objects.create(
            feed=parent_comment.feed,
            author=user,
            reply_content=reply_content,
            parent=parent_comment
        )
        return JsonResponse({
            "status": "success",
            "reply": {
                "id": new_reply.id,
                "author_name": new_reply.author.name,
                "reply_content": new_reply.reply_content,
                "created_at": new_reply.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    else:
        return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)


@csrf_exempt
def comment_update(request, comment_id):
    if request.method == "POST":
        user_email = request.session.get("user_email")
        if not user_email:
            return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
        try:
            user = Signup.objects.get(email=user_email)
        except Signup.DoesNotExist:
            return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)
        try:
            comment = Reply.objects.get(id=comment_id)
        except Reply.DoesNotExist:
            return JsonResponse({"status": "error", "message": "댓글을 찾을 수 없습니다."}, status=404)
        if comment.author != user:
            return JsonResponse({"status": "error", "message": "수정 권한이 없습니다."}, status=403)
        new_content = request.POST.get("content", "").strip()
        if not new_content:
            return JsonResponse({"status": "error", "message": "수정할 내용을 입력해 주세요."}, status=400)
        comment.reply_content = new_content
        comment.save()
        return JsonResponse({
            "status": "success",
            "comment": {
                "id": comment.id,
                "author_name": comment.author.name,
                "reply_content": comment.reply_content,
                "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    else:
        return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)


@csrf_exempt
def comment_delete(request, comment_id):
    if request.method == "POST":
        user_email = request.session.get("user_email")
        if not user_email:
            return JsonResponse({"status": "error", "message": "로그인이 필요합니다."}, status=401)
        try:
            user = Signup.objects.get(email=user_email)
        except Signup.DoesNotExist:
            return JsonResponse({"status": "error", "message": "회원 정보를 찾을 수 없습니다."}, status=400)
        try:
            comment = Reply.objects.get(id=comment_id)
        except Reply.DoesNotExist:
            return JsonResponse({"status": "error", "message": "댓글을 찾을 수 없습니다."}, status=404)
        if comment.author != user:
            return JsonResponse({"status": "error", "message": "삭제 권한이 없습니다."}, status=403)
        comment.delete()
        return JsonResponse({"status": "success", "message": "댓글이 삭제되었습니다."})
    else:
        return JsonResponse({"status": "error", "message": "POST 요청만 허용됩니다."}, status=405)

def feed_detail_modal(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    # 피드 상세보기에서 모달에 표시할 부분만 렌더링합니다.
    # 기존 feed_detail.html의 내용을 재활용하되, 모달에 적합하도록 불필요한 네비게이션 등은 제외합니다.
    return render(request, "planner/feed_detail_modal.html", {"feed": feed})
