"""Content for the narrated Video Tutorial: a slideshow walkthrough of
the app, read aloud via the browser's built-in text-to-speech (no paid
video/audio generation involved -- see services/video_tutorial.py).
English text was authored by hand; Arabic and French are Gemini
translations of it, reviewed for plausibility, then hardcoded here so
the tutorial loads instantly and doesn't re-translate on every view.
"""

SLIDES = {
    "English": [
        {"icon": "🏥", "title": "Welcome", "text": "Welcome to the Health Services Portal! This short walkthrough will show you around. Let's get started.", "visual": "grid", "focus": -1},
        {"icon": "📋", "title": "Patient Profile", "text": "Start here, at Patient Profile. Add your conditions, medications, supplements, and goals. Every other service uses this to personalize itself just for you.", "visual": "grid", "focus": 0},
        {"icon": "🩺", "title": "Bloodwork Analysis", "text": "Next is Bloodwork Analysis. Upload a photo or PDF of a lab report, and it reads the values for you. Review them, save, and see which results need attention.", "visual": "grid", "focus": 1},
        {"icon": "🏋️", "title": "Fitness Coach", "text": "Fitness Coach helps you build a workout routine, or answer a few questions for an AI-suggested plan. It tracks your calories burned too.", "visual": "grid", "focus": 2},
        {"icon": "📅", "title": "Conditions Tracker", "text": "Use Conditions Tracker to log symptoms on a calendar for anything you're monitoring. After a few entries, it can spot patterns and possible triggers.", "visual": "grid", "focus": 3},
        {"icon": "🍽️", "title": "Plate Score", "text": "Plate Score scores your meals. Just take a photo of your food, and get an instant calorie and nutrition breakdown.", "visual": "grid", "focus": 4},
        {"icon": "👥", "title": "Community Hub", "text": "The last card is the Community Hub. Tap it any time to share your journey, connect with friends, and message them privately.", "visual": "grid", "focus": 5},
        {"icon": "🤝", "title": "Adding Friends", "text": "Inside the Hub's Friends tab, search for someone by username and tap Add. Once they accept, you can message them privately.", "visual": "friends"},
        {"icon": "🌍", "title": "Share Your Journey", "text": "In the Public Feed, post your wins, your progress, or advice for others — and read what everyone else shares to stay inspired.", "visual": "feed"},
        {"icon": "✅", "title": "You're all set", "text": "That's the tour! Find dark mode, your language, and account settings any time from the Menu. Enjoy exploring.", "visual": "none"},
    ],
    "Arabic": [
        {"icon": "🏥", "title": "أهلاً بك", "text": "أهلاً بك في بوابة الخدمات الصحية! ستأخذك هذه الجولة السريعة في نظرة عامة. لنبدأ الان.", "visual": "grid", "focus": -1},
        {"icon": "📋", "title": "ملف المريض", "text": "ابدأ من هنا، في ملف المريض. أضف حالاتك الصحية، والأدوية، والمكملات، وأهدافك. تستخدم جميع الخدمات الأخرى هذه المعلومات لتخصيص تجربتك خصيصاً لك.", "visual": "grid", "focus": 0},
        {"icon": "🩺", "title": "تحليل الدم", "text": "التالي هو تحليل الدم. قم برفع صورة أو ملف PDF لتقرير المختبر، وسيقوم بقراءة القيم نيابة عنك. راجعها، واحفظها، وتعرف على النتائج التي تحتاج إلى اهتمام.", "visual": "grid", "focus": 1},
        {"icon": "🏋️", "title": "مدرب اللياقة", "text": "يساعدك مدرب اللياقة في بناء روتين تماريني، أو أجب عن بضع أسئلة للحصول على خطة مقترحة بواسطة الذكاء الاصطناعي. كما أنه يتتبع السعرات الحرارية المحروقة أيضاً.", "visual": "grid", "focus": 2},
        {"icon": "📅", "title": "متتبع الحالات", "text": "استخدم متتبع الحالات لتسجيل الأعراض على التقويم لأي شيء تتابعه. بعد بضع إدخالات، يمكنه رصد الأنماط والمحفزات المحتملة.", "visual": "grid", "focus": 3},
        {"icon": "🍽️", "title": "تقييم الطبق", "text": "يقوم تقييم الطبق بتقييم وجباتك. فقط التقاط صورة لطعامك، واحصل على تحليل فوري للسعرات الحرارية والقيم الغذائية.", "visual": "grid", "focus": 4},
        {"icon": "👥", "title": "مركز المجتمع", "text": "البطاقة الأخيرة هي مركز المجتمع. انقر عليها في أي وقت لمشاركة رحلتك، والتواصل مع الأصدقاء، ومراسلتهم بشكل خاص.", "visual": "grid", "focus": 5},
        {"icon": "🤝", "title": "إضافة الأصدقاء", "text": "داخل تبويب الأصدقاء في مركز المجتمع، ابحث عن شخص باسم المستخدم واضغط على إضافة. بمجرد قبول الطلب، يمكنك مراسلته بشكل خاص.", "visual": "friends"},
        {"icon": "🌍", "title": "شارك رحلتك", "text": "في الخلاصة العامة، انشر إنجازاتك، أو تقدمك، أو نصائحك للآخرين - واقرأ ما يشاركه الجميع لتظل ملهمًا.", "visual": "feed"},
        {"icon": "✅", "title": "أنت جاهز تماماً", "text": "هذه هي الجولة! يمكنك العثور على الوضع الليلي، ولغتك المفضلة، وإعدادات الحساب في أي وقت من القائمة. استمتع بالاستكشاف.", "visual": "none"},
    ],
    "French": [
        {"icon": "🏥", "title": "Bienvenue", "text": "Bienvenue sur le portail des services de santé ! Cette courte visite guidée va vous faire découvrir l'application. C'est parti !", "visual": "grid", "focus": -1},
        {"icon": "📋", "title": "Profil du patient", "text": "Commencez ici, sur le Profil du patient. Ajoutez vos conditions médicales, vos médicaments, vos compléments et vos objectifs. Tous les autres services s'en servent pour personnaliser votre expérience.", "visual": "grid", "focus": 0},
        {"icon": "🩺", "title": "Analyse sanguine", "text": "Voici ensuite l'Analyse sanguine. Importez une photo ou un PDF de vos résultats de labo, et l'application lit les valeurs pour vous. Consultez-les, enregistrez-les et découvrez celles qui méritent votre attention.", "visual": "grid", "focus": 1},
        {"icon": "🏋️", "title": "Coach sportif", "text": "Le Coach sportif vous aide à créer votre routine d'entraînement, ou à répondre à quelques questions pour obtenir un plan suggéré par IA. Il suit aussi vos calories brûlées.", "visual": "grid", "focus": 2},
        {"icon": "📅", "title": "Suivi des symptômes", "text": "Utilisez le Suivi des symptômes pour consigner vos ressentis sur un calendrier pour tout ce que vous surveillez. Après quelques saisies, il peut repérer des schémas et des déclencheurs possibles.", "visual": "grid", "focus": 3},
        {"icon": "🍽️", "title": "Score de l'assiette", "text": "Le Score de l'assiette évalue vos repas. Prenez simplement une photo de votre plat et obtenez instantanément le détail des calories et des nutriments.", "visual": "grid", "focus": 4},
        {"icon": "👥", "title": "Espace communautaire", "text": "La dernière carte est l'Espace communautaire. Touchez-le à tout moment pour partager votre parcours, vous connecter avec des amis et leur envoyer des messages privés.", "visual": "grid", "focus": 5},
        {"icon": "🤝", "title": "Ajouter des amis", "text": "Dans l'onglet Amis de la communauté, cherchez quelqu'un par son nom d'utilisateur et touchez Ajouter. Une fois sa demande acceptée, vous pourrez lui envoyer des messages privés.", "visual": "friends"},
        {"icon": "🌍", "title": "Partagez votre parcours", "text": "Dans le fil public, publiez vos victoires, vos progrès ou des conseils pour les autres, et lisez les partages des membres pour rester motivé.", "visual": "feed"},
        {"icon": "✅", "title": "Vous êtes prêt", "text": "C'est tout pour la visite ! Retrouvez le mode sombre, votre langue et les paramètres de votre compte à tout moment dans le Menu. Bonne exploration !", "visual": "none"},
    ],
}

UI_EXTRA = {
    "English": {"add_label": "Add", "post_label": "Post", "search_placeholder": "e.g. alexr", "sample_name": "Alex Rivera", "sample_username": "@alexr", "sample_post_author": "Jordan", "sample_post_text": "Hit my step goal 5 days in a row! Small wins add up.", "friends_label": "Friends", "public_feed_label": "Public Feed"},
    "Arabic": {"add_label": "إضافة", "post_label": "نشر", "search_placeholder": "مثال: ahmads", "sample_name": "أحمد السالم", "sample_username": "@ahmads", "sample_post_author": "يوسف", "sample_post_text": "حققت هدف الخطوات 5 أيام متتالية! الانتصارات الصغيرة تتراكم.", "friends_label": "الأصدقاء", "public_feed_label": "المنشورات العامة"},
    "French": {"add_label": "Ajouter", "post_label": "Publier", "search_placeholder": "ex. lucasd", "sample_name": "Lucas Durand", "sample_username": "@lucasd", "sample_post_author": "Julie", "sample_post_text": "Objectif de pas atteint 5 jours d'affilée ! Les petites victoires s'additionnent.", "friends_label": "Amis", "public_feed_label": "Fil public"},
}

UI_TEXT = {
    "English": {"heading": "🎬 Video Tutorial", "play": "▶ Play", "pause": "⏸ Pause", "prev": "⏮ Prev", "next": "Next ⏭", "slide_of": "Slide {i} of {n}", "note": "Auto-advancing walkthrough with on-screen captions instead of narration. Press Play to start, or step through manually."},
    "Arabic": {"heading": "🎬 الجولة المرئية", "play": "▶ تشغيل", "pause": "⏸ إيقاف", "prev": "⏮ السابق", "next": "التالي ⏭", "slide_of": "الشريحة {i} من {n}", "note": "جولة تعريفية تنتقل تلقائياً مع نصوص على الشاشة بدلاً من التعليق الصوتي. اضغط على تشغيل للبدء، أو تصفح يدوياً."},
    "French": {"heading": "🎬 Visite vidéo", "play": "▶ Lecture", "pause": "⏸ Pause", "prev": "⏮ Précédent", "next": "Suivant ⏭", "slide_of": "Diapositive {i} sur {n}", "note": "Visite guidée à défilement automatique avec des sous-titres à l'écran au lieu de la narration. Appuyez sur Lecture pour commencer, ou avancez manuellement."},
}
