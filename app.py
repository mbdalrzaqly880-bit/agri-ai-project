# ==============================================================================
# app.py - الملف الرئيسي لتشغيل موقع Flask
# ==============================================================================
# هذا الملف هو "قلب" التطبيق. لما تشغّله، يفتح سيرفر محلي على جهازك
# ويربط كل رابط (URL) بدالة بايثون تحدد وش يصير لما حد يزور هذا الرابط
# ==============================================================================

# نستورد الأدوات اللي نحتاجها من مكتبة Flask
# session: تخزن بيانات صغيرة (زي "المستخدم مسجل دخول برقم كذا") بمتصفح
#          الزائر نفسه، تخلينا نعرف "مين مسجل دخول" بكل صفحة يزورها
# redirect و url_for: نستخدمهم عشان "نحوّل" المستخدم لصفحة ثانية بعد
#          حدث معيّن (مثلاً بعد تسجيل الدخول بنجاح، نحوّله للصفحة الرئيسية)
from flask import Flask, render_template, request, session, redirect, url_for

# أدوات تشفير كلمة المرور - **لازم نستخدمها دائماً** ولا نخزن كلمة
# المرور الحقيقية أبداً بقاعدة البيانات (لو انسرقت قاعدة البيانات يوماً،
# ما يقدر أحد يعرف كلمات المرور الحقيقية للمستخدمين)
from werkzeug.security import generate_password_hash, check_password_hash

# نستورد قاعدة البيانات والجداول اللي عرّفناها بملف database/models.py
from database.models import db, User, Diagnosis

# نستورد أداة os عشان نحسب المسار الكامل (المطلق) لملف قاعدة البيانات
import os

# load_dotenv تقرأ ملف .env وتحمّل كل المتغيرات فيه (زي GEMINI_API_KEY)
# كأنها متغيرات نظام عادية، عشان os.environ.get() يقدر يوصلها لاحقاً
from dotenv import load_dotenv
load_dotenv()

# نستورد دالة التواصل مع Gemini API اللي بنيناها بملف utils/gemini_helper.py
from utils.gemini_helper import ask_gemini

# نستورد دالة التنبؤ بالموديل الحقيقي (نوع الفاكهة + السلامة + النضج + العلاج)
from model.model_utils import predict_fruit

# ننشئ التطبيق (Application) - هذا السطر لازم يكون موجود بكل مشروع Flask
# __name__ يخبر Flask وين يدور على مجلدات templates و static
app = Flask(__name__)

# ------------------------------------------------------------------------------
# إعدادات قاعدة البيانات والجلسات (Session)
# ------------------------------------------------------------------------------
# نحسب مسار المجلد اللي فيه app.py نفسه (بغض النظر عن مكان تشغيل الأمر)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# secret_key ضروري لتشفير بيانات الجلسة (session) - بدونه ميزة "تذكرني
# مسجل دخول" ما تشتغل بأمان. لاحقاً وقت الرفع الفعلي للسيرفر، لازم
# تخليه قيمة عشوائية طويلة ومخفية (مو مكتوبة بالكود مباشرة)
app.config['SECRET_KEY'] = 'yemen-agri-project-secret-key-change-later'

# نبني مسار قاعدة البيانات كمسار مطلق كامل، بدل مسار نسبي قد ينكسر
db_path = os.path.join(BASE_DIR, 'database', 'database.db')

# نتأكد إن مجلد database موجود فعلياً على القرص، وإلا ننشئه
# (exist_ok=True يمنع أي خطأ لو المجلد كان موجود أصلاً)
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

# نربط قاعدة البيانات بتطبيق Flask
db.init_app(app)

# ننشئ الجداول فعلياً بقاعدة البيانات (لو ما كانت موجودة أصلاً)
# app_context() ضروري لأن SQLAlchemy يحتاج "يعرف" هو شغال جوه أي تطبيق
with app.app_context():
    db.create_all()


# ------------------------------------------------------------------------------
# دالة مساعدة: تجيب بيانات المستخدم المسجل دخول حالياً (لو موجود)
# ------------------------------------------------------------------------------
# بنستخدمها بكل صفحة نحتاج نعرف فيها "مين المستخدم الحالي"
def get_current_user():
    user_id = session.get('user_id')  # نقرأ رقم المستخدم من الجلسة
    if user_id:
        return User.query.get(user_id)  # نجيب بياناته الكاملة من قاعدة البيانات
    return None


# ------------------------------------------------------------------------------
# متغير عام يوصل تلقائياً لكل الصفحات (Context Processor)
# ------------------------------------------------------------------------------
# بدل ما نكتب current_user=get_current_user() في كل render_template،
# هذي الدالة تخلي current_user متاح تلقائياً بكل قوالب HTML (base.html
# يستخدمه فعلاً بجملة "{% if current_user %}")
@app.context_processor
def inject_current_user():
    return {'current_user': get_current_user()}


# ------------------------------------------------------------------------------
# الرابط الأول: الصفحة الرئيسية
# ------------------------------------------------------------------------------
# @app.route('/') معناها: "لما حد يدخل الرابط الرئيسي للموقع (مثلاً
# http://127.0.0.1:5000/) شغّل الدالة اللي تحته"
@app.route('/')
def index():
    # render_template تبحث عن ملف index.html داخل مجلد templates وتعرضه
    return render_template('index.html')


# ------------------------------------------------------------------------------
# باقي الروابط - لسا ما بنينا صفحاتهم، بس لازم نعرّفها هنا مؤقتاً
# عشان url_for('diagnose') وغيرها في base.html ما تعطي خطأ وقت التشغيل
# لما نبني كل صفحة فعلياً، بنرجع ونكمل الدالة الخاصة فيها
# ------------------------------------------------------------------------------

# methods=['GET', 'POST']: نخلي هذا الرابط يقبل نوعين من الطلبات
# GET: لما المستخدم بس يفتح الصفحة عادي (أول مرة، بدون ما يرفع شي)
# POST: لما المستخدم يضغط زر "افحص الصورة الآن" ويرسل النموذج
@app.route('/diagnose', methods=['GET', 'POST'])
def diagnose():
    # نجهز متغير النتيجة فارغ بالبداية - لو ما صار رفع صورة، يظل فارغ
    # وبالتالي قسم النتيجة في diagnose.html ما يظهر (بسبب {% if result %})
    result = None

    # request.method يخبرنا نوع الطلب اللي وصل الحين
    if request.method == 'POST':
        # request.files هو "القاموس" اللي فيه كل الملفات المرفوعة بالنموذج
        # 'plant_image' هو نفس الاسم اللي حطيناه بخاصية name= في input بالـ HTML
        uploaded_file = request.files.get('plant_image')

        if uploaded_file:
            # ==================================================================
            # نحفظ الصورة المرفوعة مؤقتاً على القرص (داخل static/uploads)
            # لأن الموديل (predict_fruit) يحتاج "مسار ملف" حقيقي يقرأ منه،
            # مو الملف وهو لسا بالذاكرة فقط
            # ==================================================================
            uploads_dir = os.path.join(BASE_DIR, 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)

            temp_image_path = os.path.join(uploads_dir, uploaded_file.filename)
            uploaded_file.save(temp_image_path)

            # ==================================================================
            # نستدعي الموديل الحقيقي - يرجع قاموس فيه نوع الفاكهة، النضج،
            # السلامة، ونسبة الثقة (والعلاج لو الثمرة غير سليمة)
            # ==================================================================
            try:
                result = predict_fruit(temp_image_path)
            except FileNotFoundError as e:
                # لو ملفات الموديل غير موجودة لأي سبب، نعرض رسالة واضحة
                # بدل ما يتعطل الموقع كامل برسالة خطأ تقنية غير مفهومة
                result = {
                    'fruit_type': 'غير متاح',
                    'ripeness': 'غير متاح',
                    'is_healthy': True,
                    'confidence': 0,
                }
                print("خطأ: ", str(e))

            # نحذف الصورة المؤقتة بعد التحليل مباشرة - ما نحتاج نخزنها،
            # نخزن بس بيانات النتيجة بقاعدة البيانات (توفير مساحة تخزين)
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)

            # ==================================================================
            # نحفظ هذي العملية بقاعدة البيانات - بس لو المستخدم مسجل دخول
            # (عشان نربط عملية التشخيص برقم مستخدم حقيقي بجدول users)
            # هذا يخلي لوحة التحكم تقدر تعرض إحصائيات حقيقية لاحقاً
            # ==================================================================
            current_user = get_current_user()
            if current_user:
                new_diagnosis = Diagnosis(
                    user_id=current_user.id,
                    fruit_type=result['fruit_type'],
                    ripeness=result['ripeness'],
                    is_healthy=result['is_healthy'],
                    # نخزن اسم المرض بس لو الثمرة فعلاً مصابة، وإلا نخزن قيمة فارغة
                    disease_name=None if result['is_healthy'] else result['disease_name'],
                    confidence=result['confidence']
                )
                db.session.add(new_diagnosis)
                db.session.commit()

    # نرسل متغير result مع الصفحة - Jinja2 يستخدمه داخل diagnose.html
    return render_template('diagnose.html', result=result)


@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    # ==================================================================
    # نحتفظ بسجل المحادثة داخل session (ذاكرة خاصة بكل زائر لحاله)
    # عشان لما يسأل سؤال ثاني، الموديل "يتذكر" اللي قاله قبل شوي
    # لو ما فيه سجل سابق (أول زيارة)، نبدأ بقائمة فاضية
    # ==================================================================
    if 'chat_history' not in session:
        session['chat_history'] = []

    if request.method == 'POST':
        user_message = request.form.get('message', '').strip()

        if user_message:
            # نرسل السؤال + سجل المحادثة السابق لدالة ask_gemini
            ai_reply = ask_gemini(user_message, session['chat_history'])

            # نضيف سؤال المستخدم ورد الذكاء الاصطناعي لسجل المحادثة
            # role: "user" للمستخدم و"model" لرد الذكاء الاصطناعي - هذي
            # نفس التسميات اللي يتوقعها Gemini API بالضبط
            session['chat_history'].append({'role': 'user', 'text': user_message})
            session['chat_history'].append({'role': 'model', 'text': ai_reply})

            # session.modified = True ضروري هنا لأننا عدّلنا قائمة داخل
            # session (مو استبدلناها بقيمة جديدة كاملة)، وفلاسك بعض الأحيان
            # ما يلاحظ التعديل تلقائياً إلا لو نبهناه بهذا السطر
            session.modified = True

    return render_template('chatbot.html', chat_history=session.get('chat_history', []))


@app.route('/chatbot/clear')
def clear_chat():
    # رابط بسيط يمسح سجل المحادثة، لو المستخدم يبي يبدأ محادثة جديدة من الصفر
    session['chat_history'] = []
    return redirect(url_for('chatbot'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None  # رسالة الخطأ، تبقى فارغة إلا لو صار مشكلة

    if request.method == 'POST':
        # request.form هو "القاموس" اللي فيه بيانات النموذج (غير الملفات)
        # المفاتيح (full_name, email, password) لازم تطابق بالضبط قيمة
        # name="..." اللي حطيناها بعناصر input داخل register.html
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')

        # نتحقق: هل فيه مستخدم مسجل مسبقاً بنفس الإيميل؟
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            error = 'هذا البريد الإلكتروني مسجل مسبقاً، جرّب تسجيل الدخول'
        else:
            # generate_password_hash تحوّل كلمة المرور لنص مشفّر غير قابل
            # للفك - حتى إحنا كمطورين ما نقدر نعرف كلمة المرور الأصلية
            hashed_password = generate_password_hash(password)

            # ننشئ سجل مستخدم جديد بذاكرة البرنامج (لسا ما انحفظ بقاعدة البيانات)
            new_user = User(
                full_name=full_name,
                email=email,
                password_hash=hashed_password
            )

            # db.session.add تجهزه للحفظ، و commit() تنفّذ الحفظ الفعلي بالملف
            db.session.add(new_user)
            db.session.commit()

            # نسجّل دخوله تلقائياً بعد إنشاء الحساب مباشرة (تجربة مستخدم أفضل)
            session['user_id'] = new_user.id

            # نحوّله للصفحة الرئيسية بعد نجاح التسجيل
            return redirect(url_for('index'))

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # نبحث عن مستخدم بنفس الإيميل
        user = User.query.filter_by(email=email).first()

        # check_password_hash تقارن كلمة المرور المكتوبة الآن مع النسخة
        # المشفّرة المخزنة، بدون ما تحتاج تفك التشفير أبداً
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id  # نسجل دخوله (نحفظ رقمه بالجلسة)
            return redirect(url_for('index'))
        else:
            error = 'البريد الإلكتروني أو كلمة المرور غير صحيحة'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # نحذف رقم المستخدم من الجلسة = تسجيل خروج
    return redirect(url_for('index'))


# ------------------------------------------------------------------------------
# دالة مساعدة: تتحقق إن المستخدم الحالي "أدمن"، وإلا ترجعه للصفحة الرئيسية
# ------------------------------------------------------------------------------
# نستخدمها في بداية كل رابط خاص بلوحة التحكم، عشان أي زائر عادي أو حتى
# مستخدم مسجل دخول (لكن مو أدمن) ما يقدر يدخل هذي الصفحات مباشرة بالرابط
def admin_required():
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect(url_for('index'))
    return None  # None تعني "كل شي تمام، كمّل تنفيذ الصفحة"


@app.route('/admin/dashboard')
def admin_dashboard():
    # نتحقق أول شي من صلاحية الأدمن قبل أي شي ثاني
    guard = admin_required()
    if guard:
        return guard  # لو ما كان أدمن، نرجعه فوراً (redirect) بدون أي تنفيذ إضافي

    # ==================================================================
    # نجمع الإحصائيات المطلوبة من قاعدة البيانات
    # ==================================================================
    # User.query.count() يرجع العدد الكلي لسجلات جدول users
    total_users = User.query.count()

    # نفس الفكرة لعدد عمليات التشخيص الكلي
    total_diagnoses = Diagnosis.query.count()

    # آخر 5 عمليات تشخيص صارت، مرتبة من الأحدث للأقدم
    # order_by(Diagnosis.created_at.desc()) يعني "رتب تنازلياً حسب التاريخ"
    # limit(5) يعني "خذ أول 5 نتائج بس"
    recent_diagnoses = Diagnosis.query.order_by(
        Diagnosis.created_at.desc()
    ).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_diagnoses=total_diagnoses,
        recent_diagnoses=recent_diagnoses
    )


@app.route('/admin/users')
def admin_users():
    guard = admin_required()
    if guard:
        return guard

    # نجيب كل المستخدمين، مرتبين حسب الأحدث تسجيلاً أول
    all_users = User.query.order_by(User.created_at.desc()).all()

    return render_template('admin/users.html', all_users=all_users)


@app.route('/profile')
def profile():
    user = get_current_user()

    # لو حد حاول يفتح صفحة "حسابي" وهو مو مسجل دخول، نرجعه لصفحة الدخول
    if not user:
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)


# ------------------------------------------------------------------------------
# تشغيل السيرفر
# ------------------------------------------------------------------------------
# هذا الشرط معناه: "شغّل هذا الكود بس لو نفّذت هذا الملف مباشرة"
# (مو لو استوردته من ملف ثاني) - هذي ممارسة معيارية بكل مشاريع بايثون
if __name__ == '__main__':
    # debug=True يخلي السيرفر يعيد التشغيل تلقائياً كل ما تحفظ تعديل بالكود
    # وكمان يعطيك رسائل خطأ مفصلة تسهّل عليك تصليح الأخطاء وقت التطوير
    # ملاحظة: لازم نطفّي debug=True لما نرفع الموقع فعلياً على السيرفر (Render)
    app.run(debug=True)
