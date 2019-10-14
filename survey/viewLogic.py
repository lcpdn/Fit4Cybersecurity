from django.utils.html import format_html, mark_safe

from survey.models import SurveyUser, SurveyQuestion, SurveyQuestionAnswer, SurveyUserAnswer, TranslationKey
from survey.forms import InitialStartForm, AnswerMChoice
from survey.globals import LANG_SELECT, TRANSLATION_UI
from survey.reporthelper import getRecommendations


def createUser(lang):

    user = SurveyUser()

    # prevent the use of custom languages
    langs = [x[0] for x in LANG_SELECT]
    if lang in langs:
        user.chosenLang = lang
    else:
        user.chosenLang = LANG_SELECT[0][0]

    user.save()

    return user


def handleStartSurvey(user: SurveyUser, request):

    action = '/survey/start/' + user.chosenLang
    question = TRANSLATION_UI['question']['description'][user.chosenLang.lower()]
    title = "Fit4Cybersecurity - " + TRANSLATION_UI['question']['title'][user.chosenLang.lower()]

    if request.method == 'POST':

        form = InitialStartForm(data=request.POST, lang=user.chosenLang)

        if form.is_valid():
            user.sector = form.cleaned_data['sector']
            user.e_count = form.cleaned_data['compSize']
            user.current_question = 1
            user.save()

            survey_question = SurveyQuestion.objects.order_by('qindex').first()
            try:
                answer_choices = get_answer_choices(survey_question, user.chosenLang)
            except Exception as e:
                raise e

            form = AnswerMChoice(answer_choices, lang=user.chosenLang, answers_field_type=survey_question.qtype)
            form.setUID(user.user_id)
            form.set_question_id(survey_question.id)

            action = '/survey/question'
            title += " " + str(user.current_question)
            question = TranslationKey.objects.filter(lang=user.chosenLang, key=survey_question.titleKey)[0].text

    else:
        form = InitialStartForm(lang=user.chosenLang)
        form.setUID(user.user_id)

    return {
        'title': title,
        'question': question,
        'form': form,
        'action': action,
        'userId': user.user_id,
    }

def saveAndGetQuestion(user: SurveyUser, request):

    if user.survey_done:
        return -1

    survey_questions = SurveyQuestion.objects.order_by('qindex')
    survey_question = survey_questions[user.current_question - 1]
    try:
        tuple_answers = get_answer_choices(survey_question, user.chosenLang)
    except Exception as e:
        raise e

    if request.method == 'POST' and user.current_question == int(request.POST['questionid']):

        form = AnswerMChoice(tuple_answers, data=request.POST,
                     lang=user.chosenLang, answers_field_type=survey_question.qtype)

        if form.is_valid():

            answers = form.cleaned_data['answers']
            saveAnswers(tuple_answers, answers, user)

            if user.current_question < len(survey_questions):
                user.current_question += 1
                user.save()

                survey_question = survey_questions[user.current_question - 1]
                try:
                    tuple_answers = get_answer_choices(survey_question, user.chosenLang)
                except Exception as e:
                    raise e
                form = AnswerMChoice(tuple_answers, lang=user.chosenLang, answers_field_type=survey_question.qtype)
            else:
                #FINAL QUESTION return the new interface
                user.survey_done = True
                user.save()

                return -1
    else:
        form = AnswerMChoice(tuple_answers, lang=user.chosenLang, answers_field_type=survey_question.qtype)

    form.setUID(user.user_id)
    form.set_question_id(survey_question.id)

    return {
        'title': "Fit4Cybersecurity - " + TRANSLATION_UI['question']['question'][user.chosenLang.lower()] + " " + str(user.current_question),
        'question': TranslationKey.objects.filter(lang=user.chosenLang).filter(key=survey_question.titleKey)[0].text,
        'form': form,
        'action': '/survey/question',
        'userId': user.user_id,
    }


def saveAnswers (answer_choices, answers, user):
    existinganswerids = [int(i[0]) for i in answer_choices]
    useranswers = [int(i) for i in answers]
    for a in existinganswerids:
        answer = SurveyUserAnswer()
        answer.user = user
        qanswer = SurveyQuestionAnswer.objects.filter(id=a)[0]
        answer.answer = qanswer

        answer.uvalue = 0
        if a in useranswers:
            answer.uvalue = 1

        answer.save()


def findUserById(user_id):
    return SurveyUser.objects.filter(user_id=user_id)[0]


def getRecommendationsReport(user: SurveyUser):

    report = []
    for reportRec in getRecommendations(user):
        txt = reportRec
        txt = txt.replace("\n", "<br>")
        report.append(str(txt))

    return report


def get_answer_choices(survey_question: SurveyQuestion, user_lang: str):

    tuple_answers = []

    answer_choices = SurveyQuestionAnswer.objects.order_by('aindex').filter(question=survey_question)

    for answer_choice in answer_choices:
        translation_key = TranslationKey.objects.filter(lang=user_lang, key=answer_choice.answerKey)
        if translation_key.count() == 0:
            raise Exception('The translation has to be done for the answers choices. ' +
                'Please choose an another language.')

        tuple_answers.append(
            (
                answer_choice.id,
                format_html(
                    '{}{}',
                    mark_safe('<span class="checkmark"></span>'),
                    translation_key[0].text
                )
            )
        )

    return tuple_answers
