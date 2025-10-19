import streamlit as st
st.set_page_config(
    page_title="Living Pages", 
    layout="wide",
    initial_sidebar_state="expanded"
)

import requests
import json
import random
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import time

class RelationshipLevel(Enum):
    HOSTILE = -2
    UNFRIENDLY = -1
    NEUTRAL = 0
    FRIENDLY = 1
    TRUSTED = 2
    ALLY = 3

@dataclass
class Character:
    name: str
    description: str
    relationship: RelationshipLevel = RelationshipLevel.NEUTRAL
    relationship_points: int = 0
    last_interaction: str = ""
    traits: List[str] = field(default_factory=list)
    
    def update_relationship(self, change: int):
        self.relationship_points = max(-10, min(10, self.relationship_points + change))
        if self.relationship_points <= -7:
            self.relationship = RelationshipLevel.HOSTILE
        elif self.relationship_points <= -3:
            self.relationship = RelationshipLevel.UNFRIENDLY
        elif self.relationship_points <= 2:
            self.relationship = RelationshipLevel.NEUTRAL
        elif self.relationship_points <= 6:
            self.relationship = RelationshipLevel.FRIENDLY
        elif self.relationship_points <= 9:
            self.relationship = RelationshipLevel.TRUSTED
        else:
            self.relationship = RelationshipLevel.ALLY

class WorldState:
    def __init__(self):
        self.characters: Dict[str, Character] = {}
        self.locations = ["Village Square", "Dark Forest", "Mystic Caverns", "Abandoned Tower"]
        self.current_location = "Village Square"
        self.time_of_day = "morning"
        self.quests = {}
        
    def add_character(self, name: str, description: str, traits: List[str] = None):
        if name not in self.characters:
            self.characters[name] = Character(name=name, description=description, traits=traits or [])
    
    def get_character(self, name: str) -> Optional[Character]:
        return self.characters.get(name)
    
    def update_character_relationship(self, name: str, change: int):
        if name in self.characters:
            self.characters[name].update_relationship(change)
    
    def to_dict(self):
        return {
            "characters": {name: {
                "relationship": char.relationship.name,
                "relationship_points": char.relationship_points,
                "last_interaction": char.last_interaction,
                "traits": char.traits
            } for name, char in self.characters.items()},
            "current_location": self.current_location,
            "time_of_day": self.time_of_day
        }

st.markdown("""
    <style>
    .story-container {background-color:#2d2d2d;color:#f0f0f0;padding:20px;border-radius:10px;margin-bottom:20px;max-height:400px;overflow-y:auto;font-family:'Georgia', serif;line-height:1.6;}
    .choice-btn {margin:5px;min-width:200px;}
    .header {color:#4CAF50;}
    .user-choice {color:#64B5F6;font-style:italic;}
    .narrative-event {color:#FFA000;font-weight:bold;}
    </style>
""", unsafe_allow_html=True)

LOCAL_MODEL_URL = "http://127.0.0.1:1234/v1/chat/completions"

def query_local_model(prompt: str, system_prompt: str = None) -> str:
    headers = {"Content-Type": "application/json"}
    messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
    messages.append({"role": "user", "content": prompt})
    data = {"model": "local-model", "messages": messages, "temperature":0.7, "max_tokens":500}
    try:
        response = requests.post(LOCAL_MODEL_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error querying local model: {str(e)}"

def generate_suggested_actions(story_context: str) -> List[str]:
    system_prompt = """You are an AI that suggests 3-4 possible actions a player could take next in a text-based adventure game. Keep each suggestion short (2-5 words) and action-oriented. Return them as a JSON array of strings."""
    prompt = f"""Based on this story context, suggest 3-4 possible actions. Return ONLY a JSON array of strings. Story context: {story_context}"""
    try:
        response = query_local_model(prompt, system_prompt)
        start, end = response.find('['), response.rfind(']') + 1
        if start != -1 and end != -1:
            return json.loads(response[start:end])
    except Exception as e:
        print(f"Error generating suggestions: {e}")
    return ["Look around", "Search the area", "Continue forward"]

def get_arc_hint(arc_progress: int) -> str:
    if arc_progress < 3: return "The world feels calm, but something bigger is stirring."
    elif arc_progress < 6: return "You sense unseen forces nudging you toward a hidden truth."
    else: return "The climax draws near, every choice feels heavy with consequence."

if "story" not in st.session_state:
    st.session_state.story = "You awaken in a quiet village at dawn..."
    st.session_state.choices = []
    st.session_state.arc_progress = 0
    st.session_state.suggested_actions = []
    st.session_state.last_choice = ""
    st.session_state.last_twist = ""
    st.session_state.is_loading = False
    st.session_state.world = WorldState()
    st.session_state.world.add_character("Old Man Jenkins", "An elderly villager with a long white beard and kind eyes.", ["wise","friendly","knowledgeable"])
    st.session_state.world.add_character("Captain Rourke", "The grizzled captain of the village guard, always on the lookout for trouble.", ["brave","suspicious","dutiful"])
    st.session_state.world.add_character("Mysterious Stranger", "A hooded figure who watches from the shadows.", ["mysterious","elusive","dangerous"])
    st.session_state.world.update_character_relationship("Old Man Jenkins", 2)
    st.session_state.world.update_character_relationship("Captain Rourke", -1)
    st.session_state.world.update_character_relationship("Mysterious Stranger", -3)

with st.sidebar:
    st.header("📊 Story Stats")
    col1, col2 = st.columns(2)
    col1.metric("Choices Made", len(st.session_state.choices))
    col2.metric("Arc Progress", f"{min(100, st.session_state.arc_progress*10)}%")
    st.markdown("---")
    st.header("👥 Characters")
    for char in st.session_state.world.characters.values():
        rel_color = {RelationshipLevel.HOSTILE:"#ff4b4b",RelationshipLevel.UNFRIENDLY:"#ff8c8c",RelationshipLevel.NEUTRAL:"#f0f0f0",RelationshipLevel.FRIENDLY:"#90EE90",RelationshipLevel.TRUSTED:"#4CAF50",RelationshipLevel.ALLY:"#2E7D32"}.get(char.relationship,"#f0f0f0")
        rel_icon = {RelationshipLevel.HOSTILE:"👿",RelationshipLevel.UNFRIENDLY:"😠",RelationshipLevel.NEUTRAL:"😐",RelationshipLevel.FRIENDLY:"🙂",RelationshipLevel.TRUSTED:"😊",RelationshipLevel.ALLY:"🤝"}.get(char.relationship,"❓")
        with st.expander(f"{rel_icon} {char.name} - {char.relationship.name}"):
            st.write(char.description)
            st.progress((char.relationship_points+10)/20,f"Relationship: {char.relationship.name} ({char.relationship_points})")
            if char.traits:
                cols = st.columns(3)
                for i, trait in enumerate(char.traits): cols[i%3].markdown(f"`{trait}`")
    st.markdown("---")
    st.header("🌍 World")
    st.markdown(f"**Location:** {st.session_state.world.current_location}")
    st.markdown(f"**Time of Day:** {st.session_state.world.time_of_day.title()}")
    with st.expander("🔧 Debug Info", expanded=False):
        st.json(st.session_state.world.to_dict())
        st.write("### Full Story")
        st.text_area("story_debug", value=st.session_state.story, height=200, label_visibility="collapsed")

st.title("📖 Living Pages: A Dynamic Narrative System")
st.markdown(f'<div class="story-container">{st.session_state.story}</div>', unsafe_allow_html=True)

if not st.session_state.suggested_actions:
    with st.spinner("Generating possible actions..."):
        st.session_state.suggested_actions = generate_suggested_actions(st.session_state.story)

st.subheader("What will you do next?")
cols = st.columns(2)
for i, action in enumerate(st.session_state.choices[-4:] + st.session_state.suggested_actions):
    if i<4:
        with cols[i%2]:
            if st.button(action,key=f"action_{i}",use_container_width=True):
                st.session_state.last_choice = action
                st.session_state.is_loading = True
                st.rerun()

with st.expander("Or type your own action"):
    custom_action = st.text_input("Your action:",key="custom_action")
    if st.button("Submit Custom Action"):
        if custom_action.strip():
            st.session_state.last_choice = custom_action
            st.session_state.is_loading = True
            st.rerun()

if st.session_state.is_loading and st.session_state.last_choice:
    with st.spinner("Continuing the story..."):
        user_choice = st.session_state.last_choice
        st.session_state.choices.append(user_choice)
        st.session_state.arc_progress += 1
        twist = ""
        if random.random()<0.4:
            if random.random()<0.6:
                mentioned_chars = [char for char in st.session_state.world.characters.values() if char.name.lower() in st.session_state.story.lower()]
                if mentioned_chars:
                    char = random.choice(mentioned_chars)
                    interaction_type = random.choice(["challenge","threat","warning"]) if char.relationship in [RelationshipLevel.HOSTILE, RelationshipLevel.UNFRIENDLY] else random.choice(["observe","question","comment"]) if char.relationship == RelationshipLevel.NEUTRAL else random.choice(["help","advice","gift"])
                    twist_prompt = f"Current story: {st.session_state.story}\nCharacter: {char.name}\nCharacter traits: {', '.join(char.traits)}\nRelationship: {char.relationship.name}\nGenerate a short interaction where {char.name} {interaction_type}s the player in 1-2 sentences."
                    twist = query_local_model(twist_prompt,"You are a creative writer who creates engaging character interactions.")
                    if interaction_type in ["help","advice","gift"]: st.session_state.world.update_character_relationship(char.name,1)
                    elif interaction_type in ["threat","challenge"]: st.session_state.world.update_character_relationship(char.name,-1)
                    char.last_interaction = "Just now"
            else:
                twist_prompt = f"The current story: {st.session_state.story}\nThe player chose to: {user_choice}\nGenerate a short, surprising narrative twist (1-2 sentences)."
                twist = query_local_model(twist_prompt,"You are a creative writing assistant that adds exciting twists to stories.")
                if random.random()<0.2:
                    new_char_name = query_local_model("Generate a fantasy character name (just the name, no quotes or punctuation)","You are a creative writer who invents interesting character names.").strip('"\'')
                    if new_char_name and new_char_name not in st.session_state.world.characters:
                        char_traits = random.sample(["mysterious","friendly","suspicious","wise","playful","serious","eccentric"],k=random.randint(2,4))
                        st.session_state.world.add_character(new_char_name,f"A {char_traits[0]} figure you've just encountered.",char_traits)
                        twist += f"\n\nYou notice {new_char_name} watching you from a distance..."
        arc_hint = get_arc_hint(st.session_state.arc_progress)
        twist_section = f'NARRATIVE TWIST (if any):\n{twist}\n\n' if twist else ''
        prompt = f"Continue the story based on this context:\nCURRENT STORY:\n{st.session_state.story}\nPLAYER'S ACTION:\n{user_choice}\n{twist_section}NARRATIVE ARC HINT:\n{arc_hint}\nContinue the story in a way that's engaging and maintains player agency."
        continuation = query_local_model(prompt,"You are a master storyteller. Continue the narrative engagingly in 2-4 paragraphs.")
        update_text = f"\n\n> **{user_choice}**"
        if twist: update_text += f"\n\n*{twist}*\n"
        update_text += f"\n{continuation}"
        st.session_state.story += update_text
        st.session_state.suggested_actions = []
        st.session_state.is_loading = False
        st.session_state.last_choice = ""
        st.rerun()

st.markdown("<br><br>", unsafe_allow_html=True)

with st.expander("📝 Story Log", expanded=False):
    st.write("### Story So Far")
    st.text_area("", st.session_state.story, height=200)
    st.write("### Your Choices")
    for i, choice in enumerate(st.session_state.choices, 1):
        st.write(f"{i}. {choice}")
    if st.button("Start New Game"):
        st.session_state.clear()
        st.rerun()
