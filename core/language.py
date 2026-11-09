"""Reply in whatever language the caller spoke.

Prisma v3.0 with language_code=indic-auto returns detected_language_code.
We refine it (Hindi + many English words = Hinglish) and fall back to script
detection. Fixed phrases below are used when Evon is offline; when Evon is
online it writes the reply itself in the caller's language.

The regional phrases are short and simple; have a native speaker check any
you add before a public demo."""
import re

SCRIPTS = [  # (unicode range, language)
    (r"[஀-௿]", "ta-IN"), (r"[ఀ-౿]", "te-IN"), (r"[ಀ-೿]", "kn-IN"),
    (r"[ഀ-ൿ]", "ml-IN"), (r"[ঀ-৿]", "bn-IN"), (r"[઀-૿]", "gu-IN"),
    (r"[਀-੿]", "pa-IN"), (r"[ऀ-ॿ]", "hi-IN"),
]
ROMAN_HINDI = {"hai", "hain", "ka", "ki", "ke", "nahi", "nahin", "raha", "rahi", "ho", "gaya", "gayi",
               "kya", "aur", "mein", "bhai", "bhaiya", "ji", "kar", "se", "ko", "bahut", "abhi"}

NAMES = {"hi-en": "Hinglish", "hi-IN": "Hindi", "en-IN": "English", "ta-IN": "Tamil", "te-IN": "Telugu",
         "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "bn-IN": "Bengali",
         "gu-IN": "Gujarati", "pa-IN": "Punjabi"}


def resolve(transcript: str, detected: str | None = None) -> str:
    """Best guess of the caller's language, as a Timbre language code."""
    words = re.findall(r"\w+", transcript.lower())
    latin = [w for w in words if w.isascii()]
    latin_share = len(latin) / max(len(words), 1)
    roman_hindi = sum(w in ROMAN_HINDI for w in latin)

    if detected in (None, "hi-IN", "en-IN") and latin_share > 0.6:
        return "hi-en" if roman_hindi >= 2 else "en-IN"
    if detected == "hi-IN" and latin_share > 0.25:
        return "hi-en"
    if detected in NAMES:
        return detected
    for pattern, lang in SCRIPTS:
        if re.search(pattern, transcript):
            return lang
    return "hi-en"


ACK = {
    "hi-en": "Aapki shikayat mil gayi hai, hum technician bhej rahe hain.",
    "hi-IN": "आपकी शिकायत मिल गई है, हम टेक्नीशियन भेज रहे हैं।",
    "en-IN": "We have received your complaint and are sending a technician.",
    "mr-IN": "तुमची तक्रार मिळाली आहे, आम्ही टेक्निशियन पाठवत आहोत.",
    "ta-IN": "உங்கள் புகார் கிடைத்தது, நாங்கள் டெக்னீஷியனை அனுப்புகிறோம்.",
    "te-IN": "మీ ఫిర్యాదు అందింది, మేము టెక్నీషియన్‌ను పంపుతున్నాము.",
    "kn-IN": "ನಿಮ್ಮ ದೂರು ಸಿಕ್ಕಿದೆ, ನಾವು ಟೆಕ್ನೀಷಿಯನ್ ಅನ್ನು ಕಳುಹಿಸುತ್ತಿದ್ದೇವೆ.",
    "ml-IN": "നിങ്ങളുടെ പരാതി ലഭിച്ചു, ഞങ്ങൾ ടെക്നീഷ്യനെ അയയ്ക്കുന്നു.",
    "bn-IN": "আপনার অভিযোগ পেয়েছি, আমরা টেকনিশিয়ান পাঠাচ্ছি।",
    "gu-IN": "તમારી ફરિયાદ મળી ગઈ છે, અમે ટેક્નિશિયન મોકલી રહ્યા છીએ.",
    "pa-IN": "ਤੁਹਾਡੀ ਸ਼ਿਕਾਇਤ ਮਿਲ ਗਈ ਹੈ, ਅਸੀਂ ਟੈਕਨੀਸ਼ੀਅਨ ਭੇਜ ਰਹੇ ਹਾਂ।",
}

ETA = {  # {name}, {hours}
    "hi-en": "{name} ji lagbhag {hours} mein pahunchenge.",
    "hi-IN": "{name} जी लगभग {hours} में पहुँचेंगे।",
    "en-IN": "{name} will reach you in about {hours}.",
    "mr-IN": "{name} साधारण {hours} तासांत पोहोचतील.",
    "ta-IN": "{name} சுமார் {hours} மணி நேரத்தில் வருவார்.",
    "te-IN": "{name} సుమారు {hours} గంటల్లో చేరుకుంటారు.",
    "kn-IN": "{name} ಸುಮಾರು {hours} ಗಂಟೆಯಲ್ಲಿ ತಲುಪುತ್ತಾರೆ.",
    "ml-IN": "{name} ഏകദേശം {hours} മണിക്കൂറിനുള്ളിൽ എത്തും.",
    "bn-IN": "{name} প্রায় {hours} ঘণ্টার মধ্যে পৌঁছে যাবেন।",
    "gu-IN": "{name} લગભગ {hours} કલાકમાં પહોંચી જશે.",
    "pa-IN": "{name} ਲਗਭਗ {hours} ਘੰਟਿਆਂ ਵਿੱਚ ਪਹੁੰਚ ਜਾਣਗੇ।",
}

SAFETY = {
    "hi-en": "Suraksha pehle. Machine ka main power turant band kijiye aur sabko machine se door rakhiye. "
             "Agar aag ya dhuaan hai to fire extinguisher ka istemaal kijiye aur zaroorat ho to ek sau ek par call kijiye.",
    "hi-IN": "सुरक्षा पहले। मशीन का मेन पावर तुरंत बंद कीजिए और सबको मशीन से दूर रखिए। "
             "अगर आग या धुआं है तो फायर एक्सटिंग्विशर का इस्तेमाल कीजिए और ज़रूरत हो तो एक सौ एक पर कॉल कीजिए।",
    "en-IN": "Safety first. Switch off the machine's main power now and keep everyone away from it. "
             "If there is fire or smoke, use a fire extinguisher and call one zero one if needed.",
    "mr-IN": "सुरक्षा आधी. मशीनचा मुख्य पॉवर लगेच बंद करा आणि सर्वांना मशीनपासून दूर ठेवा.",
    "ta-IN": "முதலில் பாதுகாப்பு. இயந்திரத்தின் மெயின் பவரை உடனே அணைத்து, அனைவரையும் இயந்திரத்திலிருந்து தள்ளி வையுங்கள்.",
    "te-IN": "ముందు భద్రత. మెషిన్ మెయిన్ పవర్‌ను వెంటనే ఆపివేసి, అందరినీ మెషిన్ నుండి దూరంగా ఉంచండి.",
    "kn-IN": "ಮೊದಲು ಸುರಕ್ಷತೆ. ಯಂತ್ರದ ಮುಖ್ಯ ಪವರ್ ಅನ್ನು ತಕ್ಷಣ ಆಫ್ ಮಾಡಿ ಮತ್ತು ಎಲ್ಲರನ್ನೂ ಯಂತ್ರದಿಂದ ದೂರವಿಡಿ.",
    "ml-IN": "ആദ്യം സുരക്ഷ. മെഷീന്റെ മെയിൻ പവർ ഉടൻ ഓഫ് ചെയ്യുക, എല്ലാവരെയും മെഷീനിൽ നിന്ന് അകറ്റി നിർത്തുക.",
    "bn-IN": "আগে নিরাপত্তা। মেশিনের মেইন পাওয়ার এখনই বন্ধ করুন এবং সবাইকে মেশিন থেকে দূরে রাখুন।",
    "gu-IN": "પહેલાં સલામતી. મશીનનો મેઇન પાવર તરત બંધ કરો અને બધાને મશીનથી દૂર રાખો.",
    "pa-IN": "ਪਹਿਲਾਂ ਸੁਰੱਖਿਆ। ਮਸ਼ੀਨ ਦੀ ਮੇਨ ਪਾਵਰ ਤੁਰੰਤ ਬੰਦ ਕਰੋ ਅਤੇ ਸਾਰਿਆਂ ਨੂੰ ਮਸ਼ੀਨ ਤੋਂ ਦੂਰ ਰੱਖੋ।",
}

HINGLISH_NUMBERS = ["shoonya", "ek", "do", "teen", "chaar", "paanch", "chhah", "saat", "aath", "nau", "das",
                    "gyaarah", "baarah"]
HINDI_NUMBERS = ["शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ", "दस", "ग्यारह", "बारह"]
ENGLISH_NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                   "eleven", "twelve"]


def hours_words(hours: float, lang: str) -> str:
    """ETA in words — Timbre's docs advise numbers as words for natural speech."""
    h = max(1, round(hours))
    if lang == "hi-en":
        if hours < 0.75:
            return "aadhe ghante"
        return f"{HINGLISH_NUMBERS[h]} ghante" if h < 13 else "kuch ghanton"
    if lang == "hi-IN":
        if hours < 0.75:
            return "आधे घंटे"
        return f"{HINDI_NUMBERS[h]} घंटे" if h < 13 else "कुछ घंटों"
    if lang == "en-IN":
        if hours < 0.75:
            return "half an hour"
        return (f"{ENGLISH_NUMBERS[h]} hour" + ("s" if h > 1 else "")) if h < 13 else "a few hours"
    return str(h)  # the regional ETA templates already contain the word "hours"


def ack(lang: str) -> str:
    return ACK.get(lang, ACK["hi-en"])


def eta_sentence(lang: str, name: str, hours: float) -> str:
    return ETA.get(lang, ETA["hi-en"]).format(name=name, hours=hours_words(hours, lang))


def safety_alert(lang: str) -> str:
    return SAFETY.get(lang, SAFETY["hi-en"])
