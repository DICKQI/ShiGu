import io
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


def compress_image(image_field, max_size_kb=300, quality=85):
    """
    压缩图片到指定大小（KB）以下。
    
    如果图片本身已经小于 max_size_kb，则不需要压缩。
    
    Args:
        image_field: Django ImageField 或 InMemoryUploadedFile
        max_size_kb: 最大文件大小（KB），默认 300KB
        quality: 初始压缩质量（1-100），默认 85
        
    Returns:
        压缩后的 InMemoryUploadedFile 或 None（如果不需要压缩）
    """
    if not image_field:
        return None
        
    # 如果文件大小已经小于目标大小，不需要压缩
    max_size_bytes = max_size_kb * 1024
    
    # 检查当前文件大小
    image_field.seek(0)
    # 获取文件大小的可靠方法
    if hasattr(image_field, 'size'):
        current_size = image_field.size
    else:
        # 如果是文件对象，需要读取全部内容来获取大小
        image_field.seek(0, 2)  # 移动到文件末尾
        current_size = image_field.tell()
        image_field.seek(0)  # 移回开头
    
    if current_size <= max_size_bytes:
        image_field.seek(0)
        return None
    
    # 读取图片
    image_field.seek(0)
    image = Image.open(image_field)
    
    # 如果是 RGBA 模式，转换为 RGB（JPEG 不支持透明度）
    if image.mode in ('RGBA', 'LA', 'P'):
        # 创建白色背景
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
        image = rgb_image
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # 逐步压缩直到达到目标大小
    output = io.BytesIO()
    current_quality = quality
    
    # 首先尝试使用原始尺寸
    image.save(output, format='JPEG', quality=current_quality, optimize=True)
    file_size = output.tell()
    
    # 如果还是太大，逐步降低质量
    while file_size > max_size_bytes and current_quality > 10:
        current_quality -= 5
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=current_quality, optimize=True)
        file_size = output.tell()
    
    # 如果降低质量还不够，需要缩小尺寸
    if file_size > max_size_bytes:
        width, height = image.size
        scale_factor = 0.9
        resized_image = image  # 初始化，防止未定义
        
        while file_size > max_size_bytes and scale_factor > 0.3:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            resized_image.save(output, format='JPEG', quality=20, optimize=True)
            file_size = output.tell()
            if file_size <= max_size_bytes:
                break
            scale_factor -= 0.1
        
        image = resized_image
        # 重新生成最终的 output
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=20, optimize=True)
    
    # 准备文件对象
    output.seek(0)
    
    # 创建 InMemoryUploadedFile
    file_name = image_field.name
    if not file_name:
        file_name = 'compressed_image.jpg'
    elif not file_name.endswith('.jpg') and not file_name.endswith('.jpeg'):
        # 确保文件扩展名为 .jpg
        file_name = file_name.rsplit('.', 1)[0] + '.jpg'
    
    # 获取压缩后文件的实际大小
    output.seek(0, 2)  # 移动到文件末尾
    file_size = output.tell()
    output.seek(0)  # 移回开头
    
    compressed_file = InMemoryUploadedFile(
        output,
        'ImageField',
        file_name,
        'image/jpeg',
        file_size,
        None
    )
    
    return compressed_file

