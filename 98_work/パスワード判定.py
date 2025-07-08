pw=input('パスワードを入力してください')
if pw.isascii():
    pw_len=len(pw)
    if pw.isalnum():
        if 2<=pw_len<=4:
            print('セキュリティ程度:低')
        elif 5<=pw_len<=7:
            print('セキュリティ程度:中')
        elif 8<=pw_len<=15:
            print('セキュリティ程度:高')
        else:
            print('半角英数字15文字以内で入力してください')
    else:
        print('半角の記号は使えません')
else:
    print('全角の文字や記号は使えません')
    
                  