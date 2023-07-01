import dotenv
import json
from chat_gpt_service import ChatGPTService
from input_listener import InputListener
import pvporcupine
import struct
import os
import pyaudio
import openai
from time import sleep

dotenv.load_dotenv(".env")

SECRET_SAUCE_PROMPT = os.environ.get("PROMPT")

from tts_service import TextToSpeechService

config = json.load(open("config.json"))
openai.api_key = config["openai_key"]
if "openai_org" in config:
    openai.organization = config["openai_org"]


class WakeWordDetector:
    def __init__(self, library_path, model_path, keyword_paths):
        init_prompt = SECRET_SAUCE_PROMPT

        self.chat_gpt_service = ChatGPTService(prompt=init_prompt)

        # load access key from config
        pv_access_key = config["pv_access_key"]

        self.handle = pvporcupine.create(
            access_key=pv_access_key,
            # You will need to create your own models with your account on picovoice.ai
            # Then use as following:
            keyword_paths=[
                "/home/pi/VoiceBotChatGPT-RaspberryPI/Hey-buddy_en_raspberry-pi_v2_2_0.ppn",
                "/home/pi/VoiceBotChatGPT-RaspberryPI/Hey-KITT_en_raspberry-pi_v2_2_0.ppn",
            ],
        )

        self.pa = pyaudio.PyAudio()
        # init listener, use values from config or default
        self.listener = InputListener(
            config["silence_threshold"] if "silence_threshold" in config else 75,
            config["silence_duration"] if "silence_duration" in config else 1.5,
        )

        # get from config, or default
        sound_card_name = (
            config["sound_card_name"]
            if "sound_card_name" in config
            else "seeed-2mic-voicecard"
        )

        # Find the device index of the sound card
        print("Looking for sound card...")
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            print(device_info["name"])
            if sound_card_name in device_info["name"]:
                print("Found sound card! Using device index: %d" % i)
                self.input_device_index = i
                break
        else:
            raise Exception("Could not find sound device")

        self.speech = TextToSpeechService()  # self.input_device_index)

        self._init_audio_stream()

    def _init_audio_stream(self):
        self.audio_stream = self.pa.open(
            rate=self.handle.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.handle.frame_length,
        )

    def run(self):
        try:
            while True:
                pcm = self.audio_stream.read(self.handle.frame_length)
                pcm = struct.unpack_from("h" * self.handle.frame_length, pcm)
                porcupine_keyword_index = self.handle.process(pcm)
                if porcupine_keyword_index >= 0:
                    print("Wake word detected!")
                    self.audio_stream.close()
                    self.audio_stream = None

                    audio_path = self.listener.listen()
                    print("Transcribing...")

                    audio_file = open(audio_path, "rb")

                    transcript = openai.Audio.translate("whisper-1", audio_file)
                    print(transcript)

                    print("Sending to chat GPT...")
                    response = self.chat_gpt_service.send_to_chat_gpt(
                        transcript["text"]
                    )
                    print(response)

                    print("Playing response...")
                    # play response
                    self.speech.speak(response)

                    # delete file
                    os.remove(audio_path)
                    self._init_audio_stream()

                    print("Listening for wake word...")

        except KeyboardInterrupt:
            pass
        finally:
            if self.audio_stream is not None:
                self.audio_stream.close()
            if self.pa is not None:
                self.pa.terminate()
            self.handle.delete()


if __name__ == "__main__":
    library_path = "/path/to/porcupine/library"
    model_path = "/path/to/porcupine/model"
    keyword_paths = ["/path/to/porcupine/keyword"]

    running = True

    while running:
        try:
            detector = WakeWordDetector(library_path, model_path, keyword_paths)
            detector.run()
        except Exception as e:
            print(e)
            print("Some error. Waiting and restarting")
            sleep(1)
