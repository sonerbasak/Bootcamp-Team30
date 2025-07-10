# from dotenv import load_dotenv
# import os
# from google.generativeai import GenerativeModel, configure
# import asyncio

# load_dotenv()
# configure(api_key=os.getenv("GEMINI_API_KEY"))

# async def generate_quiz(topic: str, count: int = 5) -> str:
#     model = GenerativeModel("gemini-pro")

#     prompt = f"""
#     {topic} hakkında {count} adet Türkçe çoktan seçmeli soru hazırla.
#     Her soru şu yapıda olsun:

#     Soru:
#     A)
#     B)
#     C)
#     D)
#     Doğru Cevap: X
#     """

#     response = await model.generate_content_async(prompt)
#     return response.text
