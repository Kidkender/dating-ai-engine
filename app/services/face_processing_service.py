import logging
from typing import Optional, Tuple
from PIL import Image  # type: ignore
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN  # type: ignore
from numpy import typing as npt

logger = logging.getLogger(__name__)


class FaceProcessingService:
    """Service for face detection and embedding extraction"""

    def __init__(self, min_confidence: float = 0.7):
        """
        Initialize face processing service

        Args:
            min_confidence: Minimum confidence threshold for face detection
        """

        self.min_confidence = min_confidence
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.mtcnn = MTCNN(
            image_size=160,
            margin=0,
            min_face_size=20,
            thresholds=[0.6, 0.7, 0.7],
            factor=0.709,
            post_process=True,
            device=self.device,
        )

        self.facenet = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)

        logger.info(f"face processing service initialized on device: {self.device}")

    def detect_face(
        self, image: Image.Image
    ) -> Tuple[bool, Optional[torch.Tensor], Optional[float]]:
        """
        Detect face in image using MTCNN

        Args:
            image: PIL Image object

        Returns:
            Tuple of (face_detected, face_tensor, confidence)
        """
        try:
            face_tensor, prob = self.mtcnn(image, return_prob=True)

            if face_tensor is None or prob is None:
                logger.debug("No face detected in image")
                return False, None, None

            confidence = float(prob)
            if confidence < self.min_confidence:
                logger.debug(
                    f"Face confidence {confidence:.3f} below threshold {self.min_confidence}"
                )

                return False, None, confidence
            logger.debug(f"Face detected with confidence: {confidence:.3f}")
            return True, face_tensor, confidence

        except Exception as e:
            logger.error(f"Error detecting face: {e}")
            return False, None, None

    def extract_embedding(  # type: ignore
        self, face_tensor: torch.Tensor
    ) -> Optional[npt.NDArray[np.ndarray]]:  # type: ignore
        """
        Extract face embedding using FaceNet

        Args:
            face_tensor: Face tensor from MTCNN (shape: [3, 160, 160])

        Returns:
            Numpy array of shape (512,) or None if extraction fails
        """
        try:
            # Add batch dimension if needed
            if face_tensor.dim() == 3:
                face_tensor = face_tensor.unsqueeze(0)

            # Move to device
            face_tensor = face_tensor.to(self.device)

            # Extract embedding
            with torch.no_grad():
                embedding = self.facenet(face_tensor)

            # Convert to numpy and flatten
            embedding_np = embedding.cpu().numpy().flatten()

            if embedding_np.shape[0] != 512:
                logger.error(f"Unexpected embedding shape: {embedding_np.shape}")
                return None

            logger.debug(f"Extracted embedding with shape: {embedding_np.shape}")
            return embedding_np

        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
            return None

    def extract_facial_attributes(  # type: ignore
        self, face_tensor: torch.Tensor, image: Image.Image
    ) -> dict:  # type: ignore
        """
        Extract facial attributes from face tensor

        Args:
            face_tensor: Face tensor from MTCNN
            image: Original PIL Image

        Returns:
            Dictionary of facial attributes
        """
        try:
            # Basic attributes (placeholder - can be extended with more sophisticated models)
            attributes = {  # type: ignore
                "face_detected": True,
                "image_size": {"width": image.width, "height": image.height},
                "face_tensor_shape": list(face_tensor.shape),
                # Add more attributes here if needed:
                # - age estimation
                # - gender prediction
                # - emotion detection
                # - facial landmarks
                # - etc.
            }

            return attributes  # type: ignore

        except Exception as e:
            logger.error(f"Error extracting facial attributes: {e}")
            return {"error": str(e)}  # type: ignore

    def process_image(  # type: ignore
        self, image: Image.Image
    ) -> Tuple[bool, Optional[np.ndarray], Optional[float], dict]:  # type: ignore
        """
        Complete pipeline: detect face, extract embedding and attributes

        Args:
            image: PIL Image object

        Returns:
            Tuple of (success, embedding, confidence, attributes)
        """
        try:
            # Detect face
            face_detected, face_tensor, confidence = self.detect_face(image)

            if not face_detected or face_tensor is None:
                return False, None, confidence, {"face_detected": False}  # type: ignore

            # Extract embedding
            embedding = self.extract_embedding(face_tensor)  # type: ignore
            if embedding is None:
                return (
                    False,
                    None,
                    confidence,
                    {"face_detected": True, "embedding_failed": True},
                )  # type: ignore

            # Extract attributes
            attributes = self.extract_facial_attributes(face_tensor, image)  # type: ignore
            attributes["face_confidence"] = confidence

            return True, embedding, confidence, attributes  # type: ignore

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return False, None, None, {"error": str(e)}  # type: ignore

    def validate_face_quality(
        self, confidence: float, embedding: Optional[np.ndarray]  # type: ignore
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate face quality

        Args:
            confidence: Face detection confidence
            embedding: Face embedding array

        Returns:
            Tuple of (is_valid, error_message)
        """
        if confidence < self.min_confidence:
            return (
                False,
                f"Confidence {confidence:.3f} below threshold {self.min_confidence}",
            )

        if embedding is None:
            return False, "Embedding extraction failed"

        if embedding.shape[0] != 512:
            return False, f"Invalid embedding shape: {embedding.shape}"

        # Check for zero or invalid embeddings
        if np.all(embedding == 0):
            return False, "Embedding is all zeros"

        if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):  # type: ignore
            return False, "Embedding contains NaN or Inf values"

        return True, None
