import google.generativeai as genai
import json
from typing import List, Dict
from functions.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

# BURADA DEĞİŞİKLİK: Fonksiyonun parametrelerini güncelliyoruz
async def generate_quiz_from_gemini(quiz_type: str, quiz_name: str, count: int) -> List[Dict]:
    """Gemini API'den quiz soruları üretir ve JSON olarak parse eder."""
    categories = [
        "Tarih", "Doğal Güzellikler", "Yapılar", "Tarım Ürünü ve Yemekler", "Genel Bilgiler"
    ]
    questions_per_category = count // len(categories)
    remaining_questions = count % len(categories)

    prompt_parts = []
    for i, category in enumerate(categories):
        num_questions = questions_per_category
        if i < remaining_questions:
            num_questions += 1
        prompt_parts.append(f"**{category}** kategorisinden {num_questions} adet soru oluştur.")

    # BURADA DEĞİŞİKLİK: Prompt metnini type ve name'e göre ayarlıyoruz
    target_entity = ""
    if quiz_type == "country" and quiz_name:
        target_entity = f"{quiz_name} ülkesi"
    elif quiz_type == "city" and quiz_name:
        target_entity = f"{quiz_name} şehri"
    else:
        target_entity = "genel kültür" # Varsayılan

    base_prompt = f"""
    {target_entity} hakkında aşağıdaki kategorilerden belirtilen sayıda Türkçe çoktan seçmeli soru oluştur.
    Toplamda **tam olarak {count} adet** soru oluşturduğunu kontrol et. Ne bir eksik ne bir fazla.
    Her soru kesin olarak 4 şıklı olsun (A, B, C, D). 4 şıktan az veya fazla şık olmasın.
    Her sorunun cevabı, sadece doğru şıkkın harfi (A, B, C veya D) olsun.

    Her soruyu, şıklarını, doğru cevabı ve **gizli kategori bilgisini** ardında bir boş satır olacak şekilde,
    **kesinlikle aşağıdaki JSON formatına uyarak** oluştur.
    Sadece bir JSON dizisi (array) döndür, başka hiçbir metin veya açıklama ekleme.

    [
      {{
        "kategori": "[Kategori Adı Buraya Gelecek (örn: Tarih)]",
        "soru": "[Soru Metni Buraya Gelecek]",
        "a": "[Şık A Metni]",
        "b": "[Şık B Metni]",
        "c": "[Şık C Metni]",
        "d": "[Şık D Metni]",
        "cevap": "[Sadece doğru şıkkın harfi (örn: A)]"
      }},
      {{
        "kategori": "[Diğer Kategori Adı]",
        "soru": "[Diğer Soru Metni]",
        "a": "[Diğer Şık A Metni]",
        "b": "[Diğer Şık B Metni]",
        "c": "[Diğer Şık C Metni]",
        "d": "[Diğer Şık D Metni]",
        "cevap": "[Diğer Cevap Harfi]"
      }}
      // ... Diğer sorular
    ]

    Oluşturulacak kategoriler ve soru sayıları:
    {"\n".join(prompt_parts)}
    """
    print("\n" + "="*70)
    print("YAPAY ZEKAYA GÖNDERİLEN PROMPT (BACKEND KONSOLU):")
    print(base_prompt)
    print("="*70 + "\n")

    response = await model.generate_content_async(base_prompt)

    try:
        json_start = response.text.find('[')
        json_end = response.text.rfind(']') + 1

        if json_start != -1 and json_end != -1:
            json_string = response.text[json_start:json_end]
            quiz_data_list = json.loads(json_string)
            return quiz_data_list
        else:
            raise ValueError("Gemini'den gelen yanıt JSON formatında değil veya hatalı.")

    except json.JSONDecodeError as e:
        print(f"JSON Çözümleme Hatası: {e}")
        print(f"Gemini'den gelen ham yanıt: {response.text}")
        raise ValueError(f"Quiz verisi JSON olarak çözümlenemedi: {str(e)}")
    except ValueError as e:
        print(f"Yanıt Format Hatası: {e}")
        print(f"Gemini'den gelen ham yanıt: {response.text}")
        raise ValueError(f"Quiz verisi beklenen JSON formatında gelmedi: {str(e)}")