import os
import subprocess
import shutil
import speech_recognition as sr
from zhipuai import ZhipuAI

def chat_response(data):
    """
    完整的实时对话系统视频生成逻辑。
    流程：ASR → LLM → CosyVoice语音克隆 → TalkingGaussian视频生成
    """
    print("[backend.chat_engine] 收到数据：")
    for k, v in data.items():
        print(f"  {k}: {v}")

    try:
        # 步骤1：语音识别（ASR）
        input_audio = "./static/audios/input.wav"
        input_text = "./static/text/input.txt"
        os.makedirs("./static/text", exist_ok=True)
        
        if not os.path.exists(input_audio):
            print(f"[backend.chat_engine] 音频文件不存在: {input_audio}")
            return os.path.join("static", "videos", "chat_response.mp4")
        
        recognized_text = audio_to_text(input_audio, input_text)
        if not recognized_text:
            print("[backend.chat_engine] 语音识别失败")
            return os.path.join("static", "videos", "chat_response.mp4")
        
        # 步骤2：大模型生成回复
        output_text = "./static/text/output.txt"
        api_key = os.getenv('ZHIPU_API_KEY', '31af4e1567ad48f49b6d7b914b4145fb.MDVLvMiePGYLRJ7M')
        model = "glm-4-plus"
        reply_text = get_ai_response(input_text, output_text, api_key, model)
        
        if not reply_text:
            print("[backend.chat_engine] LLM回复生成失败")
            return os.path.join("static", "videos", "chat_response.mp4")
        
        # 步骤3：语音克隆（CosyVoice）
        # 获取参考音频路径
        voice_clone_ref = data.get('voice_clone', './voice_clone/CosyVoice-main/asset/zero_shot_prompt.wav')
        if not os.path.exists(voice_clone_ref):
            # 尝试使用默认路径
            voice_clone_ref = './voice_clone/CosyVoice-main/asset/zero_shot_prompt.wav'
        
        # 生成克隆音频
        os.makedirs("./static/audios", exist_ok=True)
        tts_output = "./static/audios/tts_output.wav"
        
        cloned_audio = text_to_speech_cosyvoice(
            text=reply_text,
            prompt_wav=voice_clone_ref,
            output_file=tts_output,
            language='zh'  # 可以根据需要调整
        )
        
        if not cloned_audio or not os.path.exists(cloned_audio):
            print("[backend.chat_engine] 语音克隆失败")
            return os.path.join("static", "videos", "chat_response.mp4")
        
        # 步骤4：TalkingGaussian生成视频
        # 使用相对路径格式（统一路径格式）
        model_param = data.get('model_param', 'output/talking_May')  # 改为相对路径
        dataset_path = data.get('dataset_path', 'data/May')  # 改为相对路径
        gpu_choice = data.get('gpu_choice', 'GPU0')
        audio_extractor = data.get('audio_extractor', 'deepspeech')
        
        # 调用视频生成
        video_data = {
            'model_name': 'TalkingGaussian',
            'model_param': model_param,
            'ref_audio': cloned_audio,
            'dataset_path': dataset_path,
            'gpu_choice': gpu_choice,
            'audio_extractor': audio_extractor
        }
        
        # 导入video_generator模块
        from backend.video_generator import generate_video
        video_path = generate_video(video_data)
        
        print(f"[backend.chat_engine] 完整对话流程完成，视频路径：{video_path}")
        return video_path
        
    except Exception as e:
        print(f"[backend.chat_engine] 错误: {e}")
        import traceback
        traceback.print_exc()
        return os.path.join("static", "videos", "chat_response.mp4")

def audio_to_text(input_audio, input_text):
    try:
        # 初始化识别器
        recognizer = sr.Recognizer()
        
        # 加载音频文件
        with sr.AudioFile(input_audio) as source:
            # 调整环境噪声
            recognizer.adjust_for_ambient_noise(source)
            # 读取音频数据
            audio_data = recognizer.record(source)
            
            print("正在识别语音...")
            
            # 使用Google语音识别
            text = recognizer.recognize_google(audio_data, language='zh-CN')
            
            # 将结果写入文件
            with open(input_text, 'w', encoding='utf-8') as f:
                f.write(text)
                
            print(f"语音识别完成！结果已保存到: {input_text}")
            print(f"识别结果: {text}")
            
            return text
            
    except sr.UnknownValueError:
        print("无法识别音频内容")
    except sr.RequestError as e:
        print(f"语音识别服务错误: {e}")
    except FileNotFoundError:
        print(f"音频文件不存在: {input_audio}")
    except Exception as e:
        print(f"发生错误: {e}")

def get_ai_response(input_text, output_text, api_key, model):
    try:
        client = ZhipuAI(api_key=api_key)
        with open(input_text, 'r', encoding='utf-8') as file:
            content = file.read().strip()

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}]
        )
        output = response.choices[0].message.content

        with open(output_text, 'w', encoding='utf-8') as file:
            file.write(output)

        print(f"答复已保存到: {output_text}")
        return output
    except Exception as e:
        print(f"[backend.chat_engine] LLM调用失败: {e}")
        return None

def text_to_speech_cosyvoice(text, prompt_wav, output_file, language='zh', model_dir=None):
    """
    使用CosyVoice进行语音克隆
    
    Args:
        text: 要合成的文本
        prompt_wav: 参考音频路径
        output_file: 输出音频文件路径
        language: 语言类型 ('zh' 或 'en')
        model_dir: CosyVoice模型目录（可选）
    
    Returns:
        生成的音频文件路径，失败返回None
    """
    try:
        # 默认模型目录
        if model_dir is None:
            model_dir = './voice_clone/CosyVoice-main/pretrained_models/CosyVoice2-0.5B'
        
        # 检查模型目录是否存在
        if not os.path.exists(model_dir):
            print(f"[backend.chat_engine] CosyVoice模型目录不存在: {model_dir}")
            return None
        
        # 检查参考音频是否存在
        if not os.path.exists(prompt_wav):
            print(f"[backend.chat_engine] 参考音频文件不存在: {prompt_wav}")
            return None
        
        # 创建输出目录
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 构建CosyVoice调用命令
        # 注意：test_cosyvoice.py 在 TalkingGaussian 目录下，需要调整路径
        cosyvoice_script = './TalkingGaussian/test_cosyvoice.py'
        if not os.path.exists(cosyvoice_script):
            # 如果不在TalkingGaussian目录，尝试在voice_clone目录
            cosyvoice_script = './voice_clone/test_cosyvoice.py'
        
        if not os.path.exists(cosyvoice_script):
            print(f"[backend.chat_engine] 找不到CosyVoice脚本: {cosyvoice_script}")
            return None
        
        # 构建命令
        cmd = [
            'python', cosyvoice_script,
            '--model_dir', model_dir,
            '--prompt_wav', prompt_wav,
            '--prompt_text', text[:50],  # 使用文本前50字符作为prompt_text（简化处理）
            '--tts_text', text,
            '--language', language,
            '--output_file', os.path.basename(output_file)
        ]
        
        print(f"[backend.chat_engine] 执行CosyVoice命令: {' '.join(cmd)}")
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(cosyvoice_script) if os.path.dirname(cosyvoice_script) else '.'
        )
        
        print("CosyVoice标准输出:", result.stdout)
        if result.stderr:
            print("CosyVoice标准错误:", result.stderr)
        
        if result.returncode != 0:
            print(f"[backend.chat_engine] CosyVoice执行失败，退出码: {result.returncode}")
            return None
        
        # 查找生成的音频文件
        # test_cosyvoice.py 输出到 test_result/ 目录
        output_dir = os.path.join(os.path.dirname(cosyvoice_script), 'test_result')
        if not os.path.exists(output_dir):
            output_dir = 'TalkingGaussian/test_result'
        
        # 查找生成的音频文件（可能带索引）
        base_name = os.path.splitext(os.path.basename(output_file))[0]
        generated_files = []
        if os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                if f.startswith(base_name) and f.endswith('.wav'):
                    generated_files.append(os.path.join(output_dir, f))
        
        if generated_files:
            # 使用最新的文件
            latest_file = max(generated_files, key=lambda f: os.path.getctime(f))
            # 复制到目标位置
            shutil.copy(latest_file, output_file)
            print(f"[backend.chat_engine] 语音克隆完成: {output_file}")
            return output_file
        else:
            print(f"[backend.chat_engine] 未找到生成的音频文件")
            return None
            
    except Exception as e:
        print(f"[backend.chat_engine] 语音克隆错误: {e}")
        import traceback
        traceback.print_exc()
        return None