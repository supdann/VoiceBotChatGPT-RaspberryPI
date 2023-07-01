import json
import os
import boto3
import pygame


class TextToSpeechService:
    def __init__(self):
        # load AWS credentials from config file
        config = json.load(open("config.json"))

        # use polly boto3 client with the credentials
        self.polly = boto3.client(
            "polly",
            aws_access_key_id=config["aws_access_key_id"],
            aws_secret_access_key=config["aws_secret_access_key"],
            region_name=config["aws_region"],
        )

    def speak(self, text):
        # Add enclosing speak tags for proper SSML
        text = (
            '<speak><amazon:effect vocal-tract-length="+3%"><prosody pitch="+3%" rate="-1%">'
            + text
            + "</prosody></amazon:effect></speak>"
        )

        response = self.polly.synthesize_speech(
            VoiceId="Matthew",
            OutputFormat="mp3",
            Text=text,
            TextType="ssml",
        )

        with open("output.mp3", "wb") as f:
            f.write(response["AudioStream"].read())

        # play using pygame
        pygame.mixer.init()
        pygame.mixer.music.load("output.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pass

        os.remove("output.mp3")
