import os

# 函数名再次更新，以准确描述其功能
def group_combine_second_lines(source_directory, output_prefix, num_groups=4):
    """
    遍历指定目录中的所有.dat文件，跳过每个文件的第一行（标题），
    将【第二行】按顺序分组，并整合到不同的新文件中。

    参数:
    source_directory (str): 包含.dat文件的源目录路径。
    output_prefix (str):    输出文件的前缀，例如 'output' 会生成 'output_group_1.txt' 等。
    num_groups (int):       要分成的组数。
    """
    print(f"正在扫描目录: '{source_directory}'...")
    # 检查源目录是否存在
    if not os.path.isdir(source_directory):
        print(f"错误：目录 '{source_directory}' 不存在。")
        return

    # 1. 找到所有 .dat 文件
    try:
        all_files = os.listdir(source_directory)
        dat_files = [f for f in all_files if f.endswith(".dat") and os.path.isfile(os.path.join(source_directory, f))]
        
        # 2. 对文件列表进行排序，确保每次处理顺序一致
        dat_files.sort()
        
        if not dat_files:
            print("在指定目录中未找到任何 .dat 文件。")
            return
            
    except Exception as e:
        print(f"错误：读取目录时发生错误: {e}")
        return

    # 3. 创建用于存储各组第二行的列表
    grouped_lines = [[] for _ in range(num_groups)]
    files_processed_count = 0
    print(f"找到了 {len(dat_files)} 个 .dat 文件，将它们分为 {num_groups} 组进行处理...")

    # 4. 遍历排序后的文件列表，读取第二行并分组
    for index, filename in enumerate(dat_files):
        file_path = os.path.join(source_directory, filename)
        
        try:
            # --- 主要修改区域开始 ---
            # 打开文件，读取并跳过第一行，然后读取第二行
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.readline()  # 读取第一行（标题），但不做任何事，即跳过
                second_line = f.readline().strip() # 读取我们需要的第二行并去除首尾空白
            # --- 主要修改区域结束 ---
                
            if second_line:
                # 确定当前文件属于哪个组
                group_index = index % num_groups
                grouped_lines[group_index].append(second_line)
                files_processed_count += 1
                # 为了方便用户理解，显示组号为 1-4 而不是 0-3
                print(f"  [成功] 读取: {filename} -> 分配到组 {group_index + 1}")
            else:
                # 日志信息已更新，以反映正在查找第二行
                print(f"  [警告] 文件 '{filename}' 没有第二行或第二行为空，已跳过。")
        except Exception as e:
            print(f"  [错误] 处理文件 '{filename}' 失败: {e}")

    # 5. 将每个组的内容写入对应的输出文件
    print("\n--- 开始写入输出文件 ---")
    total_files_written = 0
    for i, lines in enumerate(grouped_lines):
        if lines:
            group_num = i + 1
            output_filename = f"{output_prefix}_group_{group_num}.txt"
            try:
                with open(output_filename, 'w', encoding='utf-8') as f_out:
                    f_out.write('\n'.join(lines) + '\n')
                print(f"[写入成功] {len(lines)} 行数据已写入到 '{output_filename}'")
                total_files_written += 1
            except IOError as e:
                print(f"[写入失败] 无法写入文件 '{output_filename}'. 原因: {e}")

    if total_files_written > 0:
        print(f"\n处理完成！共处理了 {files_processed_count} 个文件，生成了 {total_files_written} 个分组文件。")
    else:
        print("\n处理完成，但没有找到任何有效内容可以写入文件。")

if __name__ == "__main__":
    # --- 配置区域 ---
    # 1. 设置包含 .dat 文件的目录。'.' 代表当前目录。
    SOURCE_DIR = '.' 
    # 2. 设置输出文件的【前缀】。
    OUTPUT_PREFIX = 'combined_output_second_line'
    # 3. 设置分组的数量。
    NUM_OF_GROUPS = 4
    # --- 配置结束 ---

    # 调用修改后的最终函数
    group_combine_second_lines(SOURCE_DIR, OUTPUT_PREFIX, NUM_OF_GROUPS)