
def import_quiz_files(quiz_folder, redis_conn):
    quiz = {}
    for file in quiz_folder.iterdir():
        with open(file, encoding='koi8-r') as fh:
            question = ''
            answer = ''
            for line in fh:
                if 'Вопрос' in line:
                    while not question.endswith('\n\n'):
                        line = next(fh)
                        question += line.lstrip(' ')
                if 'Ответ' in line:
                    while not answer.endswith('\n\n'):
                        line = next(fh)
                        answer += line.lstrip(' ')
                if answer and question:
                    quiz[question.rstrip('\n')] = answer.rstrip('\n')
                    question = ''
                    answer = ''
    redis_conn.hmset('quiz', quiz)
