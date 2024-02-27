# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Classes for working with vision models."""

import base64
import dataclasses
import hashlib
import io
import json
import pathlib
import typing
from typing import Any, Dict, List, Optional, Union
import urllib

from google.cloud import storage
from google.cloud.aiplatform import initializer as aiplatform_initializer
from vertexai._model_garden import _model_garden_models
import requests


# pylint: disable=g-import-not-at-top
try:
    from IPython import display as IPython_display
except ImportError:
    IPython_display = None

try:
    from PIL import Image as PIL_Image
except ImportError:
    PIL_Image = None


_SUPPORTED_UPSCALING_SIZES = [2048, 4096]

_SUPPORTED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/bmp"}


class Image:
    """Image."""

    __module__ = "vertexai.vision_models"

    _loaded_bytes: Optional[bytes] = None
    _loaded_image: Optional["PIL_Image.Image"] = None
    _gcs_uri: Optional[str] = None

    def __init__(
        self,
        image_bytes: Optional[bytes] = None,
        gcs_uri: Optional[str] = None,
    ):
        """Creates an `Image` object.

        Args:
            image_bytes: Image file bytes. Image can be in PNG or JPEG format.
            gcs_uri: Image URI in Google Cloud Storage.
        """
        if bool(image_bytes) == bool(gcs_uri):
            raise ValueError("Either image_bytes or gcs_uri must be provided.")

        self._image_bytes = image_bytes
        self._gcs_uri = gcs_uri

    @staticmethod
    def load_from_file(location: str) -> "Image":
        """Loads image from a local file, url, or Google Cloud Storage.

        Args:
            location: Local path, url, or Google Cloud Storage uri from where to
                load the image.

        Returns:
            Loaded image as an `Image` object.
        """
        if location.startswith("https://storage.googleapis.com/"):
            location = location.replace(
                "https://storage.googleapis.com/", "gs://"
            ).replace("%20", " ")

        if location.startswith("gs://"):
            return Image(gcs_uri=location)

        # Check for image at URL
        parsed_url = urllib.parse.urlparse(location)
        if all([parsed_url.scheme, parsed_url.netloc]):
            response = requests.get(location)

            if not response.ok:
                response.raise_for_status()

            content_length = int(response.headers.get("content-length", 0))
            content_type = response.headers.get("content-type", "")

            if content_length > 20 * 1024 * 1024:
                raise ValueError("Image size exceeds 20MB limit.")

            if content_type not in _SUPPORTED_MIME_TYPES:
                raise ValueError(
                    f"Image type is not supported. Supported types {_SUPPORTED_MIME_TYPES}"
                )

            return Image(image_bytes=response.content)

        # Load image from local path
        image_bytes = pathlib.Path(location).read_bytes()
        image = Image(image_bytes=image_bytes)
        return image

    @property
    def _image_bytes(self) -> bytes:
        if self._loaded_bytes is None:
            storage_client = storage.Client(
                credentials=aiplatform_initializer.global_config.credentials
            )
            self._loaded_bytes = storage.Blob.from_string(
                uri=self._gcs_uri, client=storage_client
            ).download_as_bytes()
        return self._loaded_bytes

    @_image_bytes.setter
    def _image_bytes(self, value: bytes):
        self._loaded_bytes = value

    @property
    def _pil_image(self) -> "PIL_Image.Image":
        if self._loaded_image is None:
            self._loaded_image = PIL_Image.open(io.BytesIO(self._image_bytes))
        return self._loaded_image

    @property
    def _size(self):
        return self._pil_image.size

    def show(self):
        """Shows the image.

        This method only works when in a notebook environment.
        """
        if PIL_Image and IPython_display:
            IPython_display.display(self._pil_image)

    def save(self, location: str):
        """Saves image to a file.

        Args:
            location: Local path where to save the image.
        """
        pathlib.Path(location).write_bytes(self._image_bytes)

    def _as_base64_string(self) -> str:
        """Encodes image using the base64 encoding.

        Returns:
            Base64 encoding of the image as a string.
        """
        # ! b64encode returns `bytes` object, not ``str.
        # We need to convert `bytes` to `str`, otherwise we get service error:
        # "received initial metadata size exceeds limit"
        return base64.b64encode(self._image_bytes).decode("ascii")


class Video:
    """Video."""

    __module__ = "vertexai.vision_models"

    _loaded_bytes: Optional[bytes] = None
    _gcs_uri: Optional[str] = None

    def __init__(
        self,
        video_bytes: Optional[bytes] = None,
        gcs_uri: Optional[str] = None,
    ):
        """Creates an `Image` object.

        Args:
            video_bytes: Video file bytes. Video can be in AVI, FLV, MKV, MOV,
                MP4, MPEG, MPG, WEBM, and WMV formats.
            gcs_uri: Image URI in Google Cloud Storage.
        """
        if bool(video_bytes) == bool(gcs_uri):
            raise ValueError("Either video_bytes or gcs_uri must be provided.")

        self._video_bytes = video_bytes
        self._gcs_uri = gcs_uri

    @staticmethod
    def load_from_file(location: str) -> "Video":
        """Loads video from local file or Google Cloud Storage.

        Args:
            location: Local path or Google Cloud Storage uri from where to load
                the video.

        Returns:
            Loaded video as an `Video` object.
        """
        if location.startswith("gs://"):
            return Video(gcs_uri=location)

        video_bytes = pathlib.Path(location).read_bytes()
        video = Video(video_bytes=video_bytes)
        return video

    @property
    def _video_bytes(self) -> bytes:
        if self._loaded_bytes is None:
            storage_client = storage.Client(
                credentials=aiplatform_initializer.global_config.credentials
            )
            self._loaded_bytes = storage.Blob.from_string(
                uri=self._gcs_uri, client=storage_client
            ).download_as_bytes()
        return self._loaded_bytes

    @_video_bytes.setter
    def _video_bytes(self, value: bytes):
        self._loaded_bytes = value

    def save(self, location: str):
        """Saves video to a file.

        Args:
            location: Local path where to save the video.
        """
        pathlib.Path(location).write_bytes(self._video_bytes)

    def _as_base64_string(self) -> str:
        """Encodes video using the base64 encoding.

        Returns:
            Base64 encoding of the video as a string.
        """
        # ! b64encode returns `bytes` object, not ``str.
        # We need to convert `bytes` to `str`, otherwise we get service error:
        # "received initial metadata size exceeds limit"
        return base64.b64encode(self._video_bytes).decode("ascii")


class VideoSegmentConfig:
    """The specific video segments (in seconds) the embeddings are generated for."""

    __module__ = "vertexai.vision_models"

    start_offset_sec: int
    end_offset_sec: int
    interval_sec: int

    def __init__(
        self,
        start_offset_sec: int = 0,
        end_offset_sec: int = 120,
        interval_sec: int = 16,
    ):
        """Creates a `VideoSegmentConfig` object.

        Args:
            start_offset_sec: Start time offset (in seconds) to generate embeddings for.
            end_offset_sec: End time offset (in seconds) to generate embeddings for.
            interval_sec: Interval to divide video for generated embeddings.
        """
        self.start_offset_sec = start_offset_sec
        self.end_offset_sec = end_offset_sec
        self.interval_sec = interval_sec


class VideoEmbedding:
    """Embeddings generated from video with offset times."""

    __module__ = "vertexai.vision_models"

    start_offset_sec: int
    end_offset_sec: int
    embedding: List[float]

    def __init__(
        self, start_offset_sec: int, end_offset_sec: int, embedding: List[float]
    ):
        """Creates a `VideoEmbedding` object.

        Args:
            start_offset_sec: Start time offset (in seconds) of generated embeddings.
            end_offset_sec: End time offset (in seconds) of generated embeddings.
            embedding: Generated embedding for interval.
        """
        self.start_offset_sec = start_offset_sec
        self.end_offset_sec = end_offset_sec
        self.embedding = embedding


class ImageGenerationModel(
    _model_garden_models._ModelGardenModel  # pylint: disable=protected-access
):
    """Generates images from text prompt.

    Examples::

        model = ImageGenerationModel.from_pretrained("imagegeneration@002")
        response = model.generate_images(
            prompt="Astronaut riding a horse",
            # Optional:
            number_of_images=1,
            seed=0,
        )
        response[0].show()
        response[0].save("image1.png")
    """

    __module__ = "vertexai.preview.vision_models"

    _INSTANCE_SCHEMA_URI = "gs://google-cloud-aiplatform/schema/predict/instance/vision_generative_model_1.0.0.yaml"

    def _generate_images(
        self,
        prompt: str,
        *,
        negative_prompt: Optional[str] = None,
        number_of_images: int = 1,
        width: Optional[int] = None,
        height: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        seed: Optional[int] = None,
        base_image: Optional["Image"] = None,
        mask: Optional["Image"] = None,
        language: Optional[str] = None,
        output_gcs_uri: Optional[str] = None,
    ) -> "ImageGenerationResponse":
        """Generates images from text prompt.

        Args:
            prompt: Text prompt for the image.
            negative_prompt: A description of what you want to omit in
                the generated images.
            number_of_images: Number of images to generate. Range: 1..8.
            width: Width of the image. One of the sizes must be 256 or 1024.
            height: Height of the image. One of the sizes must be 256 or 1024.
            guidance_scale: Controls the strength of the prompt.
                Suggested values are:
                * 0-9 (low strength)
                * 10-20 (medium strength)
                * 21+ (high strength)
            seed: Image generation random seed.
            base_image: Base image to use for the image generation.
            mask: Mask for the base image.
            language: Language of the text prompt for the image. Default: None.
                Supported values are `"en"` for English, `"hi"` for Hindi,
                `"ja"` for Japanese, `"ko"` for Korean, and `"auto"` for
                automatic language detection.
            output_gcs_uri: Google Cloud Storage uri to store the generated images.

        Returns:
            An `ImageGenerationResponse` object.
        """
        # Note: Only a single prompt is supported by the service.
        instance = {"prompt": prompt}
        shared_generation_parameters = {
            "prompt": prompt,
            # b/295946075 The service stopped supporting image sizes.
            # "width": width,
            # "height": height,
            "number_of_images_in_batch": number_of_images,
        }

        if base_image:
            if base_image._gcs_uri:  # pylint: disable=protected-access
                instance["image"] = {
                    "gcsUri": base_image._gcs_uri  # pylint: disable=protected-access
                }
                shared_generation_parameters[
                    "base_image_uri"
                ] = base_image._gcs_uri  # pylint: disable=protected-access
            else:
                instance["image"] = {
                    "bytesBase64Encoded": base_image._as_base64_string()  # pylint: disable=protected-access
                }
                shared_generation_parameters["base_image_hash"] = hashlib.sha1(
                    base_image._image_bytes  # pylint: disable=protected-access
                ).hexdigest()

        if mask:
            if mask._gcs_uri:  # pylint: disable=protected-access
                instance["mask"] = {
                    "image": {
                        "gcsUri": mask._gcs_uri  # pylint: disable=protected-access
                    },
                }
                shared_generation_parameters[
                    "mask_uri"
                ] = mask._gcs_uri  # pylint: disable=protected-access
            else:
                instance["mask"] = {
                    "image": {
                        "bytesBase64Encoded": mask._as_base64_string()  # pylint: disable=protected-access
                    },
                }
                shared_generation_parameters["mask_hash"] = hashlib.sha1(
                    mask._image_bytes  # pylint: disable=protected-access
                ).hexdigest()

        parameters = {}
        max_size = max(width or 0, height or 0) or None
        if max_size:
            # Note: The size needs to be a string
            parameters["sampleImageSize"] = str(max_size)
            if height is not None and width is not None and height != width:
                parameters["aspectRatio"] = f"{width}:{height}"

        parameters["sampleCount"] = number_of_images
        if negative_prompt:
            parameters["negativePrompt"] = negative_prompt
            shared_generation_parameters["negative_prompt"] = negative_prompt

        if seed is not None:
            # Note: String seed and numerical seed give different results
            parameters["seed"] = seed
            shared_generation_parameters["seed"] = seed

        if guidance_scale is not None:
            parameters["guidanceScale"] = guidance_scale
            shared_generation_parameters["guidance_scale"] = guidance_scale

        if language is not None:
            parameters["language"] = language
            shared_generation_parameters["language"] = language

        if output_gcs_uri is not None:
            parameters["storageUri"] = output_gcs_uri
            shared_generation_parameters["storage_uri"] = output_gcs_uri

        response = self._endpoint.predict(
            instances=[instance],
            parameters=parameters,
        )

        generated_images: List["GeneratedImage"] = []
        for idx, prediction in enumerate(response.predictions):
            generation_parameters = dict(shared_generation_parameters)
            generation_parameters["index_of_image_in_batch"] = idx
            encoded_bytes = prediction.get("bytesBase64Encoded")
            generated_image = GeneratedImage(
                image_bytes=base64.b64decode(encoded_bytes) if encoded_bytes else None,
                generation_parameters=generation_parameters,
                gcs_uri=prediction.get("gcsUri"),
            )
            generated_images.append(generated_image)

        return ImageGenerationResponse(images=generated_images)

    def generate_images(
        self,
        prompt: str,
        *,
        negative_prompt: Optional[str] = None,
        number_of_images: int = 1,
        guidance_scale: Optional[float] = None,
        language: Optional[str] = None,
        seed: Optional[int] = None,
        output_gcs_uri: Optional[str] = None,
    ) -> "ImageGenerationResponse":
        """Generates images from text prompt.

        Args:
            prompt: Text prompt for the image.
            negative_prompt: A description of what you want to omit in
                the generated images.
            number_of_images: Number of images to generate. Range: 1..8.
            guidance_scale: Controls the strength of the prompt.
                Suggested values are:
                * 0-9 (low strength)
                * 10-20 (medium strength)
                * 21+ (high strength)
            language: Language of the text prompt for the image. Default: None.
                Supported values are `"en"` for English, `"hi"` for Hindi,
                `"ja"` for Japanese, `"ko"` for Korean, and `"auto"` for automatic language detection.
            seed: Image generation random seed.
            output_gcs_uri: Google Cloud Storage uri to store the generated images.

        Returns:
            An `ImageGenerationResponse` object.
        """
        return self._generate_images(
            prompt=prompt,
            negative_prompt=negative_prompt,
            number_of_images=number_of_images,
            # b/295946075 The service stopped supporting image sizes.
            width=None,
            height=None,
            guidance_scale=guidance_scale,
            language=language,
            seed=seed,
            output_gcs_uri=output_gcs_uri,
        )

    def edit_image(
        self,
        *,
        prompt: str,
        base_image: "Image",
        mask: Optional["Image"] = None,
        negative_prompt: Optional[str] = None,
        number_of_images: int = 1,
        guidance_scale: Optional[float] = None,
        language: Optional[str] = None,
        seed: Optional[int] = None,
        output_gcs_uri: Optional[str] = None,
    ) -> "ImageGenerationResponse":
        """Edits an existing image based on text prompt.

        Args:
            prompt: Text prompt for the image.
            base_image: Base image from which to generate the new image.
            mask: Mask for the base image.
            negative_prompt: A description of what you want to omit in
                the generated images.
            number_of_images: Number of images to generate. Range: 1..8.
            guidance_scale: Controls the strength of the prompt.
                Suggested values are:
                * 0-9 (low strength)
                * 10-20 (medium strength)
                * 21+ (high strength)
            language: Language of the text prompt for the image. Default: None.
                Supported values are `"en"` for English, `"hi"` for Hindi,
                `"ja"` for Japanese, `"ko"` for Korean, and `"auto"` for automatic language detection.
            seed: Image generation random seed.
            output_gcs_uri: Google Cloud Storage uri to store the edited images.

        Returns:
            An `ImageGenerationResponse` object.
        """
        return self._generate_images(
            prompt=prompt,
            negative_prompt=negative_prompt,
            number_of_images=number_of_images,
            guidance_scale=guidance_scale,
            seed=seed,
            base_image=base_image,
            mask=mask,
            language=language,
            output_gcs_uri=output_gcs_uri,
        )

    def upscale_image(
        self,
        image: Union["Image", "GeneratedImage"],
        new_size: Optional[int] = 2048,
        output_gcs_uri: Optional[str] = None,
    ) -> "Image":
        """Upscales an image.

        This supports upscaling images generated through the `generate_images()` method,
        or upscaling a new image that is 1024x1024.

        Examples::

            # Upscale a generated image
            model = ImageGenerationModel.from_pretrained("imagegeneration@002")
            response = model.generate_images(
                prompt="Astronaut riding a horse",
            )
            model.upscale_image(image=response[0])

            # Upscale a new 1024x1024 image
            my_image = Image.load_from_file("my-image.png")
            model.upscale_image(image=my_image)

        Args:
            image (Union[GeneratedImage, Image]):
                Required. The generated image to upscale.
            new_size (int):
                The size of the biggest dimension of the upscaled image. Only 2048 and 4096 are currently
                supported. Results in a 2048x2048 or 4096x4096 image. Defaults to 2048 if not provided.
            output_gcs_uri: Google Cloud Storage uri to store the upscaled images.

        Returns:
            An `Image` object.
        """

        # Currently this method only supports 1024x1024 images
        if image._size[0] != 1024 and image._size[1] != 1024:
            raise ValueError(
                "Upscaling is currently only supported on images that are 1024x1024."
            )

        if new_size not in _SUPPORTED_UPSCALING_SIZES:
            raise ValueError(
                f"Only the folowing square upscaling sizes are currently supported: {_SUPPORTED_UPSCALING_SIZES}."
            )

        instance = {"prompt": ""}

        if image._gcs_uri:  # pylint: disable=protected-access
            instance["image"] = {
                "gcsUri": image._gcs_uri  # pylint: disable=protected-access
            }
        else:
            instance["image"] = {
                "bytesBase64Encoded": image._as_base64_string()  # pylint: disable=protected-access
            }

        parameters = {
            "sampleImageSize": str(new_size),
            "sampleCount": 1,
            "mode": "upscale",
        }

        if output_gcs_uri is not None:
            parameters["storageUri"] = output_gcs_uri

        response = self._endpoint.predict(
            instances=[instance],
            parameters=parameters,
        )

        upscaled_image = response.predictions[0]

        if isinstance(image, GeneratedImage):
            generation_parameters = image.generation_parameters

        else:
            generation_parameters = {}

        generation_parameters["upscaled_image_size"] = new_size

        encoded_bytes = upscaled_image.get("bytesBase64Encoded")
        return GeneratedImage(
            image_bytes=base64.b64decode(encoded_bytes) if encoded_bytes else None,
            generation_parameters=generation_parameters,
            gcs_uri=upscaled_image.get("gcsUri"),
        )


@dataclasses.dataclass
class ImageGenerationResponse:
    """Image generation response.

    Attributes:
        images: The list of generated images.
    """

    __module__ = "vertexai.preview.vision_models"

    images: List["GeneratedImage"]

    def __iter__(self) -> typing.Iterator["GeneratedImage"]:
        """Iterates through the generated images."""
        yield from self.images

    def __getitem__(self, idx: int) -> "GeneratedImage":
        """Gets the generated image by index."""
        return self.images[idx]


_EXIF_USER_COMMENT_TAG_IDX = 0x9286
_IMAGE_GENERATION_PARAMETERS_EXIF_KEY = (
    "google.cloud.vertexai.image_generation.image_generation_parameters"
)


class GeneratedImage(Image):
    """Generated image."""

    __module__ = "vertexai.preview.vision_models"

    def __init__(
        self,
        image_bytes: Optional[bytes],
        generation_parameters: Dict[str, Any],
        gcs_uri: Optional[str] = None,
    ):
        """Creates a `GeneratedImage` object.

        Args:
            image_bytes: Image file bytes. Image can be in PNG or JPEG format.
            generation_parameters: Image generation parameter values.
            gcs_uri: Image file Google Cloud Storage uri.
        """
        super().__init__(image_bytes=image_bytes, gcs_uri=gcs_uri)
        self._generation_parameters = generation_parameters

    @property
    def generation_parameters(self):
        """Image generation parameters as a dictionary."""
        return self._generation_parameters

    @staticmethod
    def load_from_file(location: str) -> "GeneratedImage":
        """Loads image from file.

        Args:
            location: Local path from where to load the image.

        Returns:
            Loaded image as a `GeneratedImage` object.
        """
        base_image = Image.load_from_file(location=location)
        exif = base_image._pil_image.getexif()  # pylint: disable=protected-access
        exif_comment_dict = json.loads(exif[_EXIF_USER_COMMENT_TAG_IDX])
        generation_parameters = exif_comment_dict[_IMAGE_GENERATION_PARAMETERS_EXIF_KEY]
        return GeneratedImage(
            image_bytes=base_image._image_bytes,  # pylint: disable=protected-access
            generation_parameters=generation_parameters,
            gcs_uri=base_image._gcs_uri,  # pylint: disable=protected-access
        )

    def save(self, location: str, include_generation_parameters: bool = True):
        """Saves image to a file.

        Args:
            location: Local path where to save the image.
            include_generation_parameters: Whether to include the image
                generation parameters in the image's EXIF metadata.
        """
        if include_generation_parameters:
            if not self._generation_parameters:
                raise ValueError("Image does not have generation parameters.")
            if not PIL_Image:
                raise ValueError(
                    "The PIL module is required for saving generation parameters."
                )

            exif = self._pil_image.getexif()
            exif[_EXIF_USER_COMMENT_TAG_IDX] = json.dumps(
                {_IMAGE_GENERATION_PARAMETERS_EXIF_KEY: self._generation_parameters}
            )
            self._pil_image.save(location, exif=exif)
        else:
            super().save(location=location)


class ImageCaptioningModel(
    _model_garden_models._ModelGardenModel  # pylint: disable=protected-access
):
    """Generates captions from image.

    Examples::

        model = ImageCaptioningModel.from_pretrained("imagetext@001")
        image = Image.load_from_file("image.png")
        captions = model.get_captions(
            image=image,
            # Optional:
            number_of_results=1,
            language="en",
        )
    """

    __module__ = "vertexai.vision_models"

    _INSTANCE_SCHEMA_URI = "gs://google-cloud-aiplatform/schema/predict/instance/vision_reasoning_model_1.0.0.yaml"

    def get_captions(
        self,
        image: Image,
        *,
        number_of_results: int = 1,
        language: str = "en",
        output_gcs_uri: Optional[str] = None,
    ) -> List[str]:
        """Generates captions for a given image.

        Args:
            image: The image to get captions for. Size limit: 10 MB.
            number_of_results: Number of captions to produce. Range: 1-3.
            language: Language to use for captions.
                Supported languages: "en", "fr", "de", "it", "es"
            output_gcs_uri: Google Cloud Storage uri to store the captioned images.

        Returns:
            A list of image caption strings.
        """
        instance = {}

        if image._gcs_uri:  # pylint: disable=protected-access
            instance["image"] = {
                "gcsUri": image._gcs_uri  # pylint: disable=protected-access
            }
        else:
            instance["image"] = {
                "bytesBase64Encoded": image._as_base64_string()  # pylint: disable=protected-access
            }
        parameters = {
            "sampleCount": number_of_results,
            "language": language,
        }
        if output_gcs_uri is not None:
            parameters["storageUri"] = output_gcs_uri

        response = self._endpoint.predict(
            instances=[instance],
            parameters=parameters,
        )
        return response.predictions


class ImageQnAModel(
    _model_garden_models._ModelGardenModel  # pylint: disable=protected-access
):
    """Answers questions about an image.

    Examples::

        model = ImageQnAModel.from_pretrained("imagetext@001")
        image = Image.load_from_file("image.png")
        answers = model.ask_question(
            image=image,
            question="What color is the car in this image?",
            # Optional:
            number_of_results=1,
        )
    """

    __module__ = "vertexai.vision_models"

    _INSTANCE_SCHEMA_URI = "gs://google-cloud-aiplatform/schema/predict/instance/vision_reasoning_model_1.0.0.yaml"

    def ask_question(
        self,
        image: Image,
        question: str,
        *,
        number_of_results: int = 1,
    ) -> List[str]:
        """Answers questions about an image.

        Args:
            image: The image to get captions for. Size limit: 10 MB.
            question: Question to ask about the image.
            number_of_results: Number of captions to produce. Range: 1-3.

        Returns:
            A list of answers.
        """
        instance = {"prompt": question}

        if image._gcs_uri:  # pylint: disable=protected-access
            instance["image"] = {
                "gcsUri": image._gcs_uri  # pylint: disable=protected-access
            }
        else:
            instance["image"] = {
                "bytesBase64Encoded": image._as_base64_string()  # pylint: disable=protected-access
            }
        parameters = {
            "sampleCount": number_of_results,
        }

        response = self._endpoint.predict(
            instances=[instance],
            parameters=parameters,
        )
        return response.predictions


class MultiModalEmbeddingModel(_model_garden_models._ModelGardenModel):
    """Generates embedding vectors from images and videos.

    Examples::

        model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
        image = Image.load_from_file("image.png")
        video = Video.load_from_file("video.mp4")

        embeddings = model.get_embeddings(
            image=image,
            video=video,
            contextual_text="Hello world",
        )
        image_embedding = embeddings.image_embedding
        video_embeddings = embeddings.video_embeddings
        text_embedding = embeddings.text_embedding
    """

    __module__ = "vertexai.vision_models"

    _INSTANCE_SCHEMA_URI = "gs://google-cloud-aiplatform/schema/predict/instance/vision_embedding_model_1.0.0.yaml"

    def get_embeddings(
        self,
        image: Optional[Image] = None,
        video: Optional[Video] = None,
        contextual_text: Optional[str] = None,
        dimension: Optional[int] = None,
        video_segment_config: Optional[VideoSegmentConfig] = None,
    ) -> "MultiModalEmbeddingResponse":
        """Gets embedding vectors from the provided image.

        Args:
            image (Image): Optional. The image to generate embeddings for. One of
              `image`, `video`, or `contextual_text` is required.
            video (Video): Optional. The video to generate embeddings for. One of
              `image`, `video` or `contextual_text` is required.
            contextual_text (str): Optional. Contextual text for your input image or video.
              If provided, the model will also generate an embedding vector for the
              provided contextual text. The returned image and text embedding
              vectors are in the same semantic space with the same dimensionality,
              and the vectors can be used interchangeably for use cases like
              searching image by text or searching text by image. One of `image`, `video` or
              `contextual_text` is required.
            dimension (int): Optional. The number of embedding dimensions. Lower
              values offer decreased latency when using these embeddings for
              subsequent tasks, while higher values offer better accuracy.
              Available values: `128`, `256`, `512`, and `1408` (default).
            video_segment_config (VideoSegmentConfig): Optional. The specific
              video segments (in seconds) the embeddings are generated for.

        Returns:
            MultiModalEmbeddingResponse:
                The image and text embedding vectors.
        """

        if not image and not video and not contextual_text:
            raise ValueError(
                "One of `image`, `video`, or `contextual_text` is required."
            )

        instance = {}

        if image:
            if image._gcs_uri:  # pylint: disable=protected-access
                instance["image"] = {
                    "gcsUri": image._gcs_uri  # pylint: disable=protected-access
                }
            else:
                instance["image"] = {
                    "bytesBase64Encoded": image._as_base64_string()  # pylint: disable=protected-access
                }

        if video:
            if video._gcs_uri:  # pylint: disable=protected-access
                instance["video"] = {
                    "gcsUri": video._gcs_uri  # pylint: disable=protected-access
                }
            else:
                instance["video"] = {
                    "bytesBase64Encoded": video._as_base64_string()  # pylint: disable=protected-access
                }  # pylint: disable=protected-access

            if video_segment_config:
                instance["video"]["videoSegmentConfig"] = {
                    "startOffsetSec": video_segment_config.start_offset_sec,
                    "endOffsetSec": video_segment_config.end_offset_sec,
                    "intervalSec": video_segment_config.interval_sec,
                }

        if contextual_text:
            instance["text"] = contextual_text

        parameters = {}
        if dimension:
            parameters["dimension"] = dimension

        response = self._endpoint.predict(
            instances=[instance],
            parameters=parameters,
        )
        image_embedding = response.predictions[0].get("imageEmbedding")
        video_embeddings = []
        for video_embedding in response.predictions[0].get("videoEmbeddings", []):
            video_embeddings.append(
                VideoEmbedding(
                    embedding=video_embedding["embedding"],
                    start_offset_sec=video_embedding["startOffsetSec"],
                    end_offset_sec=video_embedding["endOffsetSec"],
                )
            )
        text_embedding = (
            response.predictions[0].get("textEmbedding")
            if "textEmbedding" in response.predictions[0]
            else None
        )
        return MultiModalEmbeddingResponse(
            image_embedding=image_embedding,
            video_embeddings=video_embeddings,
            _prediction_response=response,
            text_embedding=text_embedding,
        )


@dataclasses.dataclass
class MultiModalEmbeddingResponse:
    """The multimodal embedding response.

    Attributes:
        image_embedding (List[float]):
            Optional. The embedding vector generated from your image.
        video_embeddings (List[VideoEmbedding]):
            Optional. The embedding vectors generated from your video.
        text_embedding (List[float]):
            Optional. The embedding vector generated from the contextual text provided for your image or video.
    """

    __module__ = "vertexai.vision_models"

    _prediction_response: Any
    image_embedding: Optional[List[float]] = None
    video_embeddings: Optional[List[VideoEmbedding]] = None
    text_embedding: Optional[List[float]] = None


class ImageTextModel(ImageCaptioningModel, ImageQnAModel):
    """Generates text from images.

    Examples::

        model = ImageTextModel.from_pretrained("imagetext@001")
        image = Image.load_from_file("image.png")

        captions = model.get_captions(
            image=image,
            # Optional:
            number_of_results=1,
            language="en",
        )

        answers = model.ask_question(
            image=image,
            question="What color is the car in this image?",
            # Optional:
            number_of_results=1,
        )
    """

    __module__ = "vertexai.vision_models"

    # NOTE: Using this ImageTextModel class is recommended over using ImageQnAModel or ImageCaptioningModel,
    # since SDK Model Garden classes should follow the design pattern of exactly 1 SDK class to 1 Model Garden schema URI

    _INSTANCE_SCHEMA_URI = "gs://google-cloud-aiplatform/schema/predict/instance/vision_reasoning_model_1.0.0.yaml"
