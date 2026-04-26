import asyncio
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import Base, User, Assessment, Question, UserRole, DifficultyLevel


os.environ['DATABASE_URL'] = "postgresql+asyncpg://neondb_owner:npg_Lcn0zo2Raypq@ep-quiet-king-ao570j8q-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require"

engine = create_async_engine(os.getenv('DATABASE_URL'), echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── Seed Data ──────────────────────────────────────────

ASSESSMENTS = [
    {
        "title": "Fundamental Python",
        "description": "Tests core Python concepts including data types, control flow, functions, and OOP basics.",
        "category": "Backend",
        "difficulty": DifficultyLevel.EASY,
        "duration_minutes": 30,
        "pass_mark": 60,
        "max_attempts": 2,
        "is_published": True,
        "questions": [
            {
                "question_text": "What is the output of type([])?",
                "options": ["<class 'list'>", "<class 'array'>", "<class 'tuple'>", "<class 'dict'>"],
                "correct_option": 0,
                "points": 1,
                "difficulty": 1,
                "sort_order": 1,
            },
            {
                "question_text": "Which keyword is used to define a function in Python?",
                "options": ["func", "def", "function", "define"],
                "correct_option": 1,
                "points": 1,
                "difficulty": 1,
                "sort_order": 2,
            },
            {
                "question_text": "What does len([1, 2, 3]) return?",
                "options": ["2", "3", "4", "1"],
                "correct_option": 1,
                "points": 1,
                "difficulty": 1,
                "sort_order": 3,
            },
            {
                "question_text": "Which of the following is immutable in Python?",
                "options": ["list", "dict", "tuple", "set"],
                "correct_option": 2,
                "points": 1,
                "difficulty": 1,
                "sort_order": 4,
            },
            {
                "question_text": "What is the output of 2 ** 3 in Python?",
                "options": ["6", "9", "8", "5"],
                "correct_option": 2,
                "points": 1,
                "difficulty": 1,
                "sort_order": 5,
            },
            {
                "question_text": "How do you start a comment in Python?",
                "options": ["//", "/*", "#", "--"],
                "correct_option": 2,
                "points": 1,
                "difficulty": 1,
                "sort_order": 6,
            },
            {
                "question_text": "Which method adds an element to the end of a list?",
                "options": ["add()", "insert()", "append()", "extend()"],
                "correct_option": 2,
                "points": 1,
                "difficulty": 1,
                "sort_order": 7,
            },
            {
                "question_text": "What is the correct way to create a dictionary in Python?",
                "options": ["d = []", "d = ()", "d = {}", "d = <{}>"],
                "correct_option": 2,
                "points": 1,
                "difficulty": 2,
                "sort_order": 8,
            },
            {
                "question_text": "What will bool('') return?",
                "options": ["True", "False", "None", "Error"],
                "correct_option": 1,
                "points": 1,
                "difficulty": 2,
                "sort_order": 9,
            },
            {
                "question_text": "Which of these is used for exception handling in Python?",
                "options": ["try/catch", "try/except", "try/finally only", "catch/throw"],
                "correct_option": 1,
                "points": 1,
                "difficulty": 2,
                "sort_order": 10,
            },
            {
                "question_text": "What does the 'self' parameter refer to in a class method?",
                "options": [
                    "The class itself",
                    "The instance of the class",
                    "The parent class",
                    "A global variable",
                ],
                "correct_option": 1,
                "points": 2,
                "difficulty": 2,
                "sort_order": 11,
            },
            {
                "question_text": "What is the output of list(range(0, 10, 3))?",
                "options": ["[0, 3, 6, 9]", "[0, 3, 6]", "[3, 6, 9]", "[0, 3, 6, 9, 12]"],
                "correct_option": 0,
                "points": 2,
                "difficulty": 2,
                "sort_order": 12,
            },
            {
                "question_text": "What is a lambda function in Python?",
                "options": [
                    "A named function defined with def",
                    "An anonymous function defined with lambda keyword",
                    "A built-in Python function",
                    "A function that returns None",
                ],
                "correct_option": 1,
                "points": 2,
                "difficulty": 3,
                "sort_order": 13,
            },
            {
                "question_text": "What is the difference between deepcopy and shallow copy?",
                "options": [
                    "No difference",
                    "Deepcopy copies only the reference, shallow copies the object",
                    "Shallow copy copies only the reference, deepcopy copies the full object recursively",
                    "Deepcopy only works on lists",
                ],
                "correct_option": 2,
                "points": 2,
                "difficulty": 3,
                "sort_order": 14,
            },
            {
                "question_text": "What does the @staticmethod decorator do?",
                "options": [
                    "Makes the method private",
                    "Binds the method to the class instead of an instance",
                    "Defines a method that does not receive an implicit first argument",
                    "Makes the method abstract",
                ],
                "correct_option": 2,
                "points": 2,
                "difficulty": 3,
                "sort_order": 15,
            },
        ],
    },
    {
        "title": "Machine Learning",
        "description": "Covers ML fundamentals including supervised learning, model evaluation, and core algorithms.",
        "category": "Backend",
        "difficulty": DifficultyLevel.MEDIUM,
        "duration_minutes": 45,
        "pass_mark": 65,
        "max_attempts": 1,
        "is_published": True,
        "questions": [
            {
                "question_text": "What is supervised learning?",
                "options": [
                    "Learning without any data",
                    "Learning from labeled training data",
                    "Learning from unlabeled data",
                    "Learning by reinforcement only",
                ],
                "correct_option": 1,
                "points": 1,
                "difficulty": 1,
                "sort_order": 1,
            },
            {
                "question_text": "Which of the following is a classification algorithm?",
                "options": ["Linear Regression", "K-Means", "Logistic Regression", "PCA"],
                "correct_option": 2,
                "points": 1,
                "difficulty": 1,
                "sort_order": 2,
            },
            {
                "question_text": "What does overfitting mean in ML?",
                "options": [
                    "Model performs well on both train and test data",
                    "Model performs poorly on train data",
                    "Model memorizes training data and performs poorly on unseen data",
                    "Model is too simple to learn patterns",
                ],
                "correct_option": 2,
                "points": 1,
                "difficulty": 1,
                "sort_order": 3,
            },
            {
                "question_text": "What is the purpose of a train/test split?",
                "options": [
                    "To reduce dataset size",
                    "To evaluate model performance on unseen data",
                    "To improve training speed",
                    "To balance classes",
                ],
                "correct_option": 1,
                "points": 1,
                "difficulty": 1,
                "sort_order": 4,
            },
            {
                "question_text": "Which metric is best for imbalanced classification problems?",
                "options": ["Accuracy", "F1 Score", "Mean Squared Error", "R-squared"],
                "correct_option": 1,
                "points": 1,
                "difficulty": 2,
                "sort_order": 5,
            },
            {
                "question_text": "What does K in K-Nearest Neighbors represent?",
                "options": [
                    "Number of features",
                    "Number of clusters",
                    "Number of nearest data points to consider",
                    "Learning rate",
                ],
                "correct_option": 2,
                "points": 1,
                "difficulty": 2,
                "sort_order": 6,
            },
            {
                "question_text": "What is the role of a loss function in ML?",
                "options": [
                    "To preprocess input data",
                    "To measure how far predictions are from actual values",
                    "To split data into batches",
                    "To normalize features",
                ],
                "correct_option": 1,
                "points": 1,
                "difficulty": 2,
                "sort_order": 7,
            },
            {
                "question_text": "What is gradient descent?",
                "options": [
                    "An algorithm to find the maximum of a function",
                    "An optimization algorithm that minimizes loss by updating weights",
                    "A technique to split data",
                    "A type of neural network layer",
                ],
                "correct_option": 1,
                "points": 2,
                "difficulty": 2,
                "sort_order": 8,
            },
            {
                "question_text": "What is regularization used for?",
                "options": [
                    "To increase model complexity",
                    "To speed up training",
                    "To reduce overfitting by penalizing large weights",
                    "To normalize input features",
                ],
                "correct_option": 2,
                "points": 2,
                "difficulty": 2,
                "sort_order": 9,
            },
            {
                "question_text": "Which of the following is an unsupervised learning algorithm?",
                "options": ["Decision Tree", "Random Forest", "K-Means Clustering", "Logistic Regression"],
                "correct_option": 2,
                "points": 1,
                "difficulty": 2,
                "sort_order": 10,
            },
            {
                "question_text": "What does PCA stand for and what is it used for?",
                "options": [
                    "Predictive Class Analysis — for classification",
                    "Principal Component Analysis — for dimensionality reduction",
                    "Polynomial Coefficient Adjustment — for regression",
                    "Probabilistic Cluster Assignment — for clustering",
                ],
                "correct_option": 1,
                "points": 2,
                "difficulty": 3,
                "sort_order": 11,
            },
            {
                "question_text": "What is the bias-variance tradeoff?",
                "options": [
                    "High bias = overfitting, high variance = underfitting",
                    "High bias = underfitting, high variance = overfitting",
                    "Both bias and variance should be maximized",
                    "Bias and variance are unrelated",
                ],
                "correct_option": 1,
                "points": 2,
                "difficulty": 3,
                "sort_order": 12,
            },
            {
                "question_text": "What is cross-validation used for?",
                "options": [
                    "To train the model faster",
                    "To validate data types",
                    "To get a more reliable estimate of model performance",
                    "To split features and labels",
                ],
                "correct_option": 2,
                "points": 2,
                "difficulty": 3,
                "sort_order": 13,
            },
            {
                "question_text": "What is a confusion matrix?",
                "options": [
                    "A matrix used for feature scaling",
                    "A table showing true vs predicted classifications",
                    "A technique for hyperparameter tuning",
                    "A visualization of loss over epochs",
                ],
                "correct_option": 1,
                "points": 2,
                "difficulty": 3,
                "sort_order": 14,
            },
            {
                "question_text": "What is the difference between bagging and boosting?",
                "options": [
                    "Bagging trains models sequentially, boosting trains in parallel",
                    "Bagging trains models in parallel independently, boosting trains sequentially where each model corrects the previous",
                    "Both are identical techniques",
                    "Bagging is only for regression, boosting only for classification",
                ],
                "correct_option": 1,
                "points": 2,
                "difficulty": 3,
                "sort_order": 15,
            },
        ],
    },
]


# ── Insert Logic ───────────────────────────────────────

async def seed():
    async with AsyncSessionLocal() as db:
        for assessment_data in ASSESSMENTS:
            questions_data = assessment_data.pop("questions")

            assessment = Assessment(
                id=uuid.uuid4(),
                title=assessment_data["title"],
                description=assessment_data["description"],
                category=assessment_data["category"],
                difficulty=assessment_data["difficulty"],
                duration_minutes=assessment_data["duration_minutes"],
                pass_mark=assessment_data["pass_mark"],
                max_attempts=assessment_data["max_attempts"],
                is_published=assessment_data["is_published"],
                total_questions=len(questions_data),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(assessment)
            await db.flush()  # get assessment.id before inserting questions

            for q in questions_data:
                question = Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text=q["question_text"],
                    options=q["options"],
                    correct_option=q["correct_option"],
                    points=q["points"],
                    difficulty=q["difficulty"],
                    sort_order=q["sort_order"],
                    created_at=datetime.now(timezone.utc),
                )
                db.add(question)

            await db.commit()
            print(f"✓ Inserted: {assessment.title} ({len(questions_data)} questions)")

        print("\n✅ Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())