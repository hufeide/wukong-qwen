
import pyaudio
import dashscope
from dashscope.audio.asr import *


# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
dashscope.api_key = "sk-3761b32fe4ad4840b784407d9238cc29"

mic = None
stream = None

class Callback(TranslationRecognizerCallback):
    def on_open(self) -> None:
        global mic
        global stream
        print("TranslationRecognizerCallback open.")
        mic = pyaudio.PyAudio()
        stream = mic.open(
            format=pyaudio.paInt16, channels=1, rate=16000, input=True
        )

    def on_close(self) -> None:
        global mic
        global stream
        print("TranslationRecognizerCallback close.")
        stream.stop_stream()
        stream.close()
        mic.terminate()
        stream = None
        mic = None

    def on_event(
        self,
        request_id,
        transcription_result: TranscriptionResult,
        translation_result: TranslationResult,
        usage,
    ) -> None:
        print("request id: ", request_id)
        print("usage: ", usage)
        if translation_result is not None:
            print(
                "translation_languages: ",
                translation_result.get_language_list(),
            )
            english_translation = translation_result.get_translation("en")
            print("sentence id: ", english_translation.sentence_id)
            print("translate to english: ", english_translation.text)
            if english_translation.stash is not None:
                print(
                    "translate to english stash: ",
                    translation_result.get_translation("en").stash.text,
                )
        if transcription_result is not None:
            print("sentence id: ", transcription_result.sentence_id)
            print("transcription: ", transcription_result.text)
            if transcription_result.stash is not None:
                print("transcription stash: ", transcription_result.stash.text)


callback = Callback()


translator = TranslationRecognizerRealtime(
    model="gummy-realtime-v1",
    format="pcm",
    sample_rate=16000,
    transcription_enabled=True,
    translation_enabled=True,
    translation_target_languages=["en"],
    callback=callback,
)
translator.start()
print("请您通过麦克风讲话体验实时语音识别和翻译功能")
while True:
    if stream:
        data = stream.read(3200, exception_on_overflow=False)
        translator.send_audio_frame(data)
    else:
        break

translator.stop()