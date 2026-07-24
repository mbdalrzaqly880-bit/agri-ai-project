# ==============================================================================
# database/models.py
# ==============================================================================
# هذا الملف يحدد "شكل" الجداول بقاعدة البيانات باستخدام SQLAlchemy
# بدل ما نكتب جمل SQL يدوياً (CREATE TABLE users (...))، نعرّف "class"
# بايثون عادي، والمكتبة تتكفل بتحويله لجدول حقيقي بقاعدة البيانات
# هذا الأسلوب يسمى ORM (Object-Relational Mapping)
# ==============================================================================

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ننشئ كائن قاعدة البيانات - بنربطه بتطبيق Flask لاحقاً داخل app.py
db = SQLAlchemy()


# ------------------------------------------------------------------------------
# جدول المستخدمين (User)
# ------------------------------------------------------------------------------
# db.Model تخبر SQLAlchemy: "هذا الكلاس يمثل جدول حقيقي بقاعدة البيانات"
class User(db.Model):
    __tablename__ = 'users'  # اسم الجدول الفعلي بقاعدة البيانات

    # كل سطر تحت يمثل "عمود" (column) بالجدول

    # id: رقم تعريفي فريد لكل مستخدم، يزيد تلقائياً (1, 2, 3...)
    # primary_key=True تعني هذا العمود هو "المفتاح الأساسي" للجدول
    id = db.Column(db.Integer, primary_key=True)

    # الاسم الكامل للمستخدم
    full_name = db.Column(db.String(100), nullable=False)

    # البريد الإلكتروني - unique=True تمنع تسجيل نفس الإيميل مرتين
    email = db.Column(db.String(120), unique=True, nullable=False)

    # كلمة المرور - **مهم جداً**: ما نخزن كلمة المرور الحقيقية أبداً!
    # نخزن نسخة "مشفّرة" (hash) منها فقط - نشرح هذا أكثر بملف auth
    password_hash = db.Column(db.String(255), nullable=False)

    # تاريخ إنشاء الحساب - يتحدد تلقائياً وقت التسجيل
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # is_admin: يحدد هل هذا الحساب "أدمن" (صاحب الموقع) يقدر يدخل لوحة
    # التحكم، أو مستخدم عادي. القيمة الافتراضية False لكل حساب جديد
    is_admin = db.Column(db.Boolean, default=False)

    # علاقة (Relationship): كل مستخدم ممكن يكون له عدة عمليات تشخيص
    # هذا يربط جدول User بجدول Diagnosis (بنسويه لاحقاً) تلقائياً
    diagnoses = db.relationship('Diagnosis', backref='user', lazy=True)

    # دالة تساعدنا نطبع بيانات المستخدم بشكل مقروء وقت الاختبار (Debug)
    def __repr__(self):
        return f'<User {self.email}>'


# ------------------------------------------------------------------------------
# جدول عمليات التشخيص (Diagnosis)
# ------------------------------------------------------------------------------
# هذا الجدول يحفظ سجل كل عملية فحص صورة صارت، عشان نقدر نعرضها لاحقاً
# في لوحة التحكم (كم عملية فحص صارت، أكثر الأمراض تكراراً...)
class Diagnosis(db.Model):
    __tablename__ = 'diagnoses'

    id = db.Column(db.Integer, primary_key=True)

    # user_id: عمود يربط هذا السجل بمستخدم معيّن من جدول users
    # ForeignKey تعني "هذا الرقم لازم يكون موجود فعلاً بجدول users"
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # نوع الفاكهة المكتشفة (مانجو، موز، عنب...)
    fruit_type = db.Column(db.String(80), nullable=False)

    # حالة النضج - نص بسيط ("ناضجة" / "غير ناضجة")
    ripeness = db.Column(db.String(30), nullable=False)

    # is_healthy: True لو الثمرة سليمة، False لو مصابة بمرض
    is_healthy = db.Column(db.Boolean, default=True)

    # اسم المرض - يبقى فارغ (None) لو الثمرة سليمة
    disease_name = db.Column(db.String(150), nullable=True)

    confidence = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Diagnosis {self.fruit_type} - {self.ripeness}>'
