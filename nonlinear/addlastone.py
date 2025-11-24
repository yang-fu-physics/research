import os
import collections

def group_by_frequency_and_combine(source_directory, output_directory='.'):
    """
    遍历指定目录中的所有.dat文件，根据文件名中的频率进行分组，
    并整合每个频率分组下所有文件内容的第二行到一个新的输出文件中。
    文件名格式应为 "温度-频率.dat" (例如: "300K-100Hz.dat")。
    
    参数:
    source_directory (str): 包含.dat文件的源目录路径。
    output_directory (str): 输出文件的存放目录。默认为当前目录。
    """
    print(f"正在扫描目录: '{source_directory}'...")
    # 检查源目录是否存在
    if not os.path.isdir(source_directory):
        print(f"错误：源目录 '{source_directory}' 不存在。")
        return

    # 确保输出目录存在，如果不存在则创建
    if not os.path.isdir(output_directory):
        try:
            os.makedirs(output_directory)
            print(f"已创建输出目录: '{output_directory}'")
        except OSError as e:
            print(f"错误：无法创建输出目录 '{output_directory}'。原因: {e}")
            return

    # 1. 找到所有 .dat 文件
    try:
        all_files = os.listdir(source_directory)
        dat_files = [f for f in all_files if f.endswith(".dat") and os.path.isfile(os.path.join(source_directory, f))]
        
        if not dat_files:
            print("在指定目录中未找到任何 .dat 文件。")
            return
            
        # 对文件列表进行排序，确保处理顺序一致（例如先处理低温，再处理高温）
        dat_files.sort() 
        print(f"找到了 {len(dat_files)} 个 .dat 文件。")

    except Exception as e:
        print(f"错误：读取目录时发生错误: {e}")
        return

    # 2. 创建用于存储各频率分组数据的字典
    #    collections.defaultdict(list) 可以在键不存在时自动创建一个空列表
    grouped_lines_by_freq = collections.defaultdict(list)
    files_processed_count = 0

    print("\n--- 开始解析文件名并读取数据 ---")
    # 3. 遍历文件，解析频率，读取第二行并分组
    for filename in dat_files:
        try:
            # --- 核心修改：解析文件名以获取频率 ---
            # os.path.splitext(filename)[0] 会得到不带扩展名的文件名，例如 "300K-100Hz"
            base_name = os.path.splitext(filename)[0]
            parts = base_name.split('-')
            
            # 校验文件名格式是否正确
            if len(parts) != 2:
                print(f"  [警告] 文件名 '{filename}' 格式不符合 '温度-频率' 规范，已跳过。")
                continue
            
            # temperature = parts[0] # 温度信息，此处暂未使用
            frequency = parts[1]
            
            file_path = os.path.join(source_directory, filename)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.readline()  # 跳过第一行
                second_line = f.readline().strip() # 读取第二行

            if second_line:
                # 将第二行内容添加到对应频率的列表中
                grouped_lines_by_freq[frequency].append(second_line)
                files_processed_count += 1
                print(f"  [成功] 读取: {filename} -> 分配到频率组 '{frequency}'")
            else:
                print(f"  [警告] 文件 '{filename}' 没有第二行或第二行为空，已跳过。")

        except Exception as e:
            print(f"  [错误] 处理文件 '{filename}' 失败: {e}")

    # 4. 将每个频率组的内容写入对应的输出文件
    print(f"\n--- 开始写入 {len(grouped_lines_by_freq)} 个频率分组文件 ---")
    total_files_written = 0
    # 按频率排序，确保输出顺序稳定（例如 100Hz, 200Hz, 1000Hz）
    for frequency, lines in sorted(grouped_lines_by_freq.items()):
        if lines:
            # 输出文件名直接使用频率
            output_filename = f"{frequency}.txt"
            output_path = os.path.join(output_directory, output_filename)
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f_out:
                    f_out.write('\n'.join(lines) + '\n')
                print(f"[写入成功] {len(lines)} 行数据已写入到 '{output_path}'")
                total_files_written += 1
            except IOError as e:
                print(f"[写入失败] 无法写入文件 '{output_path}'. 原因: {e}")

    if total_files_written > 0:
        print(f"\n处理完成！共处理了 {files_processed_count} 个文件，生成了 {total_files_written} 个频率分组文件。")
    else:
        print("\n处理完成，但没有找到任何有效内容可以写入文件。")

if __name__ == "__main__":
    # --- 配置区域 ---
    # 1. 设置包含 .dat 文件的目录。'.' 代表当前脚本所在的目录。
    SOURCE_DIR = '.' 
    
    # 2. 设置输出文件的【存放目录】。'output_data' 代表在当前目录下创建一个名为 output_data 的文件夹来存放结果。
    #    您也可以设置为 '.'，让输出文件和脚本在同一目录。
    OUTPUT_DIR = 'output_data'

    # --- 配置结束 ---
    
    # 调用功能更新后的函数
    group_by_frequency_and_combine(SOURCE_DIR, OUTPUT_DIR)