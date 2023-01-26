# function that converts to word
def convert_to_word(number):
    number = str(number)
    int_side = number
    dec_side = ''
    for i in range(0, len(number)):
        if number[i] == '.':
            int_side = number[:i]
            dec_side = number[i + 1:]
            break
    while not (int_side.isdigit()) or not (dec_side.isdigit()) and dec_side != '':
        dec_side = ''
        # print('Only numbers are allowed! (decimals included, but not fractions)')
        int_side = number
        for i in range(0, len(number)):
            if number[i] == '.':
                int_side = number[:i]
                dec_side = number[i + 1:]
        user_choice = input()
    int_length = len(int_side)
    ones = ['', 'one ', 'two ', 'three ', 'four ', 'five ', 'six ', 'seven ', 'eight ', 'nine ']
    teens = ['ten ', 'eleven ', 'twelve ', 'thirteen ', 'fourteen ', 'fifteen ', 'sixteen ', 'seventeen ', 'eighteen ',
             'nineteen ']
    decades = ['', '', 'twenty ', 'thirty ', 'forty ', 'fifty ', 'sixty ', 'seventy ', 'eighty ', 'ninety ']
    hundreds = ['', 'one hundred ', 'two hundred ', 'three hundred ', 'four hundred ', 'five hundred ', 'six hundred ',
                'seven hundred ', 'eight hundred ', 'nine hundred ']
    comma = ['thousand ', 'million ', 'trillion ', 'quadrillion ']
    word = ''
    int_length = len(int_side)
    dec_length = len(dec_side)
    change = int_length
    up_change = 0
    while change > 0:
        if int_side == '':
            break
        if number == '0':
            word = 'zero'
            break
        elif change > 1 and int_side[change - 2] == '1':
            for i in range(0, 10):
                if int_side[change - 1] == str(i):
                    word = teens[i] + word
        else:
            if change > 0:
                for i in range(0, 10):
                    if int_side[change - 1] == str(i):
                        word = ones[i] + word
            if change > 1:
                for i in range(0, 10):
                    if int_side[change - 2] == str(i):
                        word = decades[i] + word
        if change > 2:
            for i in range(0, 10):
                if int_side[change - 3] == str(i):
                    word = hundreds[i] + word
        if change > 3:
            word = comma[up_change] + word
        change -= 3
        up_change += 1
    # word += 'birr '

    print(dec_side)
    """
    for i in range(0, len(dec_side)):
        for x in range(0, 10):
            if dec_side[i] == str(x):
                word += ones[x]"""

    if dec_side not in ['', '0', '00']:
        word += 'birr and '
        word += convert_to_word(dec_side) + " cents"

    word += " only"

    return word.title()
