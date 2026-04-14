import grpc
import time
import riva.proto.riva_asr_pb2 as rasr
import riva.proto.riva_asr_pb2_grpc as rasr_grpc
import riva.proto.riva_audio_pb2 as raudio
from dotenv import load_dotenv
import os
load_dotenv()  # Tải biến môi trường từ file .env

RIVA_OFFLINE_ASR_HOST =  os.getenv("RIVA_OFFLINE_ASR_HOST", "localhost:50051")

class RivaASRClient:
    def __init__(self, server_address=RIVA_OFFLINE_ASR_HOST):
        self.channel = grpc.insecure_channel(server_address)
        self.stub = rasr_grpc.RivaSpeechRecognitionStub(self.channel)

    def get_recognition_config(self, language_code="vi-VN", sample_rate=16000):
        """Tạo cấu hình chung cho cả 2 chế độ"""
        return rasr.RecognitionConfig(
            encoding=raudio.LINEAR_PCM,
            sample_rate_hertz=sample_rate,
            language_code=language_code,
            max_alternatives=1,
            enable_automatic_punctuation=False,
            enable_word_time_offsets=True, # Lấy timestamp từng từ,
            language_code='vi-VN'
        )

    # --- CHẾ ĐỘ 1: OFFLINE (BATCH RECOGNITION) ---
    def recognize_offline(self, audio_path):
        print(f"\n[OFFLINE] Đang xử lý file: {audio_path}...")
        
        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        # Tạo request đơn lẻ chứa toàn bộ audio
        request = rasr.RecognizeRequest(
            config=self.get_recognition_config(),
            audio=audio_data
        )

        try:
            response = self.stub.Recognize(request)
            for result in response.results:
                print(f"Kết quả: {result.alternatives[0].transcript}")
                print(f"Độ tin cậy: {result.alternatives[0].confidence:.2f}")
        except grpc.RpcError as e:
            print(f"Lỗi Offline: {e.details()}")

    # --- CHẾ ĐỘ 2: ONLINE (STREAMING RECOGNITION) ---
    def recognize_online(self, audio_path):
        print(f"\n[ONLINE] Đang stream file: {audio_path}...")

        streaming_config = rasr.StreamingRecognitionConfig(
            config=self.get_recognition_config(),
            interim_results=True
        )

        def request_generator():
            # Bước 1: Gửi config trước
            yield rasr.StreamingRecognizeRequest(streaming_config=streaming_config)
            
            # Bước 2: Gửi từng đoạn audio (chunks)
            with open(audio_path, 'rb') as f:
                while True:
                    chunk = f.read(3200) # Khoảng 100ms âm thanh
                    if not chunk:
                        break
                    yield rasr.StreamingRecognizeRequest(audio_content=chunk)
                    time.sleep(0.05) # Giả lập tốc độ nói thực tế

        try:
            responses = self.stub.StreamingRecognize(request_generator())
            
            for response in responses:
                for result in response.results:
                    transcript = result.alternatives[0].transcript
                    if result.is_final:
                        print(f"\n[FINAL]: {transcript}")
                    else:
                        print(f"[STREAMING]: {transcript}", end='\r')
        except grpc.RpcError as e:
            print(f"Lỗi Online: {e.details()}")

# --- CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    # Đảm bảo bạn đã bật ASR NIM tại địa chỉ này
    client = RivaASRClient(RIVA_OFFLINE_ASR_HOST)
    
    # Thay 'test.wav' bằng file âm thanh 16kHz, Mono của bạn
    audio_file = "wav/output_2_20.wav" 

    # 1. Chạy Offline: Gửi 1 cục, nhận 1 cục (Dùng cho file ghi âm sẵn)
    client.recognize_offline(audio_file)

    # # 2. Chạy Online: Gửi đến đâu dịch đến đó (Dùng cho Microphone/Live stream)
    # client.recognize_online(audio_file)