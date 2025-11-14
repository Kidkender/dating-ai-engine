from facenet_pytorch import InceptionResnetV1, MTCNN  # type: ignore
from PIL import Image  # type: ignore
import torch, os, numpy as np

mtcnn = MTCNN(image_size=160)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)

base_dir = "C:/Users/Admin/Desktop/DuckCode/Python/dataset/ALL/ALL"
subfolders = ["round1", "round2", "round3"]

embeddings = []
batch_size = 64

for sub in subfolders:
    folder_path = os.path.join(base_dir, sub)
    img_files = [
        f
        for f in os.listdir(folder_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    # print(f"Processing {sub} ({len(img_files)} images)...")

    for i in range(0, len(img_files), batch_size):
        batch_imgs = [
            Image.open(os.path.join(folder_path, f)).convert("RGB")
            for f in img_files[i : i + batch_size]
        ]
        faces = [mtcnn(img) for img in batch_imgs]
        faces = [f for f in faces if f is not None]
        if not faces:
            continue
        faces = torch.stack(faces).to(device)

        with torch.no_grad():
            batch_emb = model(faces).cpu().numpy()
        embeddings.append(batch_emb)

if embeddings:
    embeddings = np.concatenate(embeddings)
    np.save("celeba_embeddings.npy", embeddings)
    print("✅ Embeddings saved:", embeddings.shape)
else:
    print("⚠️ No faces detected in any folder.")
