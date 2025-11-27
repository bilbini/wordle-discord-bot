#!/usr/bin/env python3
"""
Script to convert SPOILER_wordle_possibles.txt into a Python list format
"""

def convert_wordle_file(input_file, output_file=None):
    """
    Convert the wordle possibles file to Python list format
    
    Args:
        input_file (str): Path to input file
        output_file (str): Path to output file (optional)
    
    Returns:
        list: List of words in Python list format
    """
    
    words = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Extract the word from lines like "  1 | aahed"
                # The word is the last part after the pipe symbol
                if '|' in line:
                    word = line.split('|')[1].strip()
                    if word:  # Only add non-empty words
                        words.append(word)
                else:
                    # If no pipe, try to get the last word-like string
                    parts = line.strip().split()
                    if parts:
                        # Take the last part which should be the word
                        word = parts[-1]
                        if word.isalpha():  # Only add if it's alphabetic
                            words.append(word)
    
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []
    
    # Create the Python list string
    list_str = "[\n"
    for i, word in enumerate(words):
        if i == len(words) - 1:
            list_str += f'  "{word}"\n'
        else:
            list_str += f'  "{word}",\n'
    list_str += "]"
    
    # Write to output file if specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(list_str)
            print(f"Successfully converted {len(words)} words to {output_file}")
        except Exception as e:
            print(f"Error writing output file: {e}")
    
    # Also print to console
    print(f"Converted {len(words)} words")
    
    return list_str

def main():
    """Main function to run the conversion"""
    input_file = "SPOILER_wordle_possibles.txt"
    output_file = "wordle_possibles_list.py"
    
    print(f"Converting {input_file} to Python list format...")
    
    result = convert_wordle_file(input_file, output_file)
    
    if result:
        print("\nFirst 50 words in the list:")
        lines = result.split('\n')
        for i in range(min(52, len(lines))):  # Show first 50 words + brackets
            print(lines[i])
        
        if len(lines) > 52:
            print("... (truncated)")
            print(lines[-1])  # Show closing bracket
    
    return result

if __name__ == "__main__":
    main()