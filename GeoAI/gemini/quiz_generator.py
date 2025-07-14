from dotenv import load_dotenv
import os
from google.generativeai import GenerativeModel, configure
import asyncio

load_dotenv()
configure(api_key=os.getenv("GEMINI_API_KEY"))

async def generate_quiz(topic: str, count: int = 5) -> str:
    model = GenerativeModel("gemini-pro")

    prompt = f"""
    {topic} hakkında {count} adet Türkçe çoktan seçmeli soru oluştur.
    Her soru kesin olarak 4 şıklı olsun. 4 şıktan az veya fazla şık olmasın.
    Cevap, sadece doğru şıkkın harfi (A, B, C veya D) olsun.
    Her soru ve şıklarını, ardında doğru cevabı ve bir boş satır olacak şekilde, **kesinlikle aşağıdaki formata uyarak** yaz:

    Soru: [Soru Metni Buraya Gelecek]
    A) [Şık A Metni]
    B) [Şık B Metni]
    C) [Şık C Metni]
    D) [Şık D Metni]
    Doğru Cevap: [Sadece doğru şıkkın harfi (örn: A)]

    Örnekler:
    Soru: Türkiye'nin başkenti neresidir?
    A) İzmir
    B) Ankara
    C) İstanbul
    D) Bursa
    Doğru Cevap: B

    Soru: Ayasofya nerededir?
    A) İstanbul
    B) Antalya
    C) İzmir
    D) Trabzon
    Doğru Cevap: A
    """

    response = await model.generate_content_async(prompt)
    return response.text