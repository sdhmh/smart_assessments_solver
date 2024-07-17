import sys

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import NoSuchElementException

from solvers import solver
from .utils import logger_setup
from .types import WebElement

LOADER = ()
RETAKE_BUTTON = ()
QUIZ_AREA_SELECTOR = ()
TOTAL_QUIZZES = ()
QUIZ_QUESTION = ()
QUIZ_OPTIONS = ()
QUIZ_SUBMIT = ()
CHECK_ANSWER_CORRECT = (
    By.XPATH,
    '//div[contains(@class, "class_of_parent") and .//i[contains(@class, "class of the grandchild")]]'
)
EXPLANATION = ()
QUIZ_LOADER = ()

# ======= SETUP LOGGER =======
logger = logger_setup(__name__)


# ============== ASSESSMENTS FUNCTIONS ===============
def load_assessment(assessment: WebElement, wait: WebDriverWait) -> None:
    """
    Loads the assessment and waits for the quiz area to appear.

    Parameters
    ----------
    assessment : `WebElement`
        The assessment element
    wait : `WebDriverWait`
        A WebDriverWait object
    solver_id : `str`, optional
        ID of the solver to use. Default is 'openai', by default None

    Returns
    -------
    None
    > 
    """
    assessment.click()
    assessment = wait.until(lambda driver: driver.find_element(*QUIZ_AREA_SELECTOR))
    retake_quiz(wait)

def retake_quiz(wait):
    driver = wait.until(lambda driver: driver)
    wait.until(EC.invisibility_of_element(LOADER))
    try:
        driver.find_element(*RETAKE_BUTTON).click()
    except NoSuchElementException:
        return
    wait.until(lambda driver: driver.find_element(*QUIZ_OPTIONS))

def solve(assessment: WebElement, wait: WebDriverWait, solver_id="openai", model="gpt-3.5-turbo"):
    """
    Solve an online quiz assessment.

    Parameters
    ----------
    assessment : WebElement
        The web element representing the assessment.
    wait : WebDriverWait
        A WebDriver Wait object used for waiting on the assessment to load.
    solver_id : str, optional
        The ID of the solver to use. Can be either "openai" or "ollama". Defaults to "openai".

    Yields
    ------
    tuple
        A tuple containing the question, options, and correct answer for each quiz.

    Returns
    -------
    None


    See Also
    --------
    get_quizzes : A function that gets all quizzes from an assessment.
    get_options : A function that gets the options for a quiz.
    submit_answer : A function that submits an answer to a quiz.
    """
    print("here now in solve")
    retake_quiz(wait)
    print("here now after solve")
    for quiz_no in get_quizzes(assessment):
        logger.info("Solving quiz %s", quiz_no)
        question, options = get_options(assessment)
        formatted_options = "\n".join([" ".join(option) for option in options])
        ask_str = f"Question: {question}\nOptions:\n{formatted_options}"
        
        while answer := solver.solve(ask_str, solver_id, model):
            correct_ans, _ = submit_answer(assessment, answer, wait)
            if not (correct_ans == "__again"):
                break

        yield {"quiz_no":quiz_no,"question": question, "options": options, "answer": correct_ans}, answer


def submit_answer(assessment: WebElement, answer, wait: WebDriverWait):
    submit_button = assessment.find_element(*QUIZ_SUBMIT)
    clicked = False
    for option in assessment.find_elements(*QUIZ_OPTIONS):
        if option.text.splitlines()[0] == answer:
            option.click()
            clicked = True

    # If there is no option clicked then that means the AI didn't give correct answer
    if not clicked:
        logger.error("Answer provided doesn't match the quiz (check the output of GenAI??)")
        while ask_again := input("Ask AI Again? [y/n]: "):
            if ask_again == "y":
                return "__again", None
            elif ask_again == "n":
                logger.error("Don't know what to do now.... Exiting.")
                sys.exit(1)
                
    logger.debug("Waiting for submit to enable for 1st")
    wait.until(EC.element_to_be_clickable(submit_button))
    submit_button.click() # Submit the answer
    
    
    wait.until(EC.presence_of_element_located(EXPLANATION))
    explanation = assessment.find_element(*EXPLANATION).text
    
    logger.debug("Validating...")
    correct_option = assessment.find_element(*CHECK_ANSWER_CORRECT)
    correct_ans = correct_option.text.splitlines()[0]
    
    logger.debug("Waiting for submit to enable for 2nd")
    wait.until(EC.invisibility_of_element(QUIZ_LOADER))
    wait.until(EC.element_to_be_clickable(submit_button))
    submit_button.click()

    return correct_ans, explanation


def get_options(assessment: WebElement) -> tuple[str, list]:
    """
    Returns a tuple containing the question as a string and a list of option texts
    extracted from an assessment element.

    Parameters
    ----------
    assessment : `selenium.webdriver.remote.webelement.WebElement`
        The Selenium WebDriver element representing the assessment.

    Returns
    -------
    (str, list)
        A tuple where the first element is the question as a string, and the second element is a list of option texts.
    """

    question = assessment.find_element(*QUIZ_QUESTION).text
    options = assessment.find_elements(*QUIZ_OPTIONS)

    return (question, [opt.text.splitlines() for opt in options])

def get_quizzes(assessment: WebElement):
    quiz_info = assessment.find_element(*TOTAL_QUIZZES).text.split()
    current = quiz_info[-3]
    total = quiz_info[-1]
    for i in range(int(total)-int(current)+1): # total = 12, current=12 so need to add 1
        yield i
