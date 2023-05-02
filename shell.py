import uzbek

while True:
    text = input('uzbek > ')
    result, error = uzbek.run('<stdin>', text)

    if error: print(error.as_string())
    else: print(result)