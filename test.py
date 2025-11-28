from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

client = genai.Client(api_key="AIzaSyDqdw7J7vHLlU0Nb_tvAmJ9955N9Y3WfTA")

response = client.models.generate_images(
    model="gemini-2.0-flash-preview-image-generation",
    prompt='Far shot of the silohouette of a kid standing by the beach',
    config=types.GenerateImagesConfig(
        number_of_images= 4,
    )
)
for generated_image in response.generated_images:
  generated_image.image.show()
print(response.generated_images[0])
